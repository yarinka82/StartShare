from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone

from backend.apps.analytics.models import EventLog

from .exceptions import InvalidTransition


INTRO_EMAIL_TEXT = (
    "[Plattform] vermittelt nur den Kontakt und ist nicht Partei von Gesprächen oder Verträgen. "
    "Bitte behandeln Sie ausgetauschte Informationen vertraulich."
)


# I1: introduction lifecycle state machine.
# This enum defines the allowed lifecycle states for a startup-investor introduction.
class IntroductionStatus(models.TextChoices):
    SUGGESTED = "SUGGESTED", "Suggested"
    INTERESTED = "INTERESTED", "Interested"
    ACCEPTED = "ACCEPTED", "Accepted"
    INTRODUCED = "INTRODUCED", "Introduced"
    DECLINED = "DECLINED", "Declined"
    EXPIRED = "EXPIRED", "Expired"


# I1: shared notice version used when the investor confirms the startup notification wording.
INTRO_NOTICE_TEXT_VERSION = "intro-notice-v1"


def assert_provider_allowed(provider_name: str = "default") -> None:
    # I3: fail-closed provider check used by the mail client before sending startup request emails.
    if not getattr(settings, "INTRO_EMAIL_PROVIDER_ALLOWED", True):
        raise ValidationError(f"Email provider '{provider_name}' is not allowed in the current environment.")


DECLINE_REASONS = {
    "sector": "sector",
    "stage": "stage",
    "region": "region",
    "check_size": "check_size",
    "team": "team",
    "numbers": "numbers",
    "other": "other",
}


# I1: single source of truth for the introduction record and lifecycle transitions.
# All status changes must go through the domain service to avoid invalid transitions.
class Introduction(models.Model):
    """Represents a single startup-investor introduction flow."""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["startup", "investor"], name="uniq_intro_startup_investor"),
        ]
        ordering = ["-created_at"]

    startup = models.ForeignKey(
        "profiles.StartupProfile",
        on_delete=models.CASCADE,
        related_name="introductions",
    )
    investor = models.ForeignKey(
        "investors.InvestorProfile",
        on_delete=models.CASCADE,
        related_name="introductions",
    )
    status = models.CharField(
        max_length=16,
        choices=IntroductionStatus.choices,
        default=IntroductionStatus.SUGGESTED,
    )
    interested_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    investor_message = models.TextField(blank=True, default="")
    decline_reason = models.CharField(max_length=40, blank=True, default="")
    sent_to_startup = models.BooleanField(default=False)
    sent_to_investor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    ALLOWED_TRANSITIONS = {
        IntroductionStatus.SUGGESTED: {IntroductionStatus.INTERESTED, IntroductionStatus.DECLINED},
        IntroductionStatus.INTERESTED: {IntroductionStatus.ACCEPTED, IntroductionStatus.DECLINED, IntroductionStatus.EXPIRED},
        IntroductionStatus.ACCEPTED: {IntroductionStatus.INTRODUCED},
    }
    CLOSED_STATUSES = {IntroductionStatus.DECLINED, IntroductionStatus.EXPIRED, IntroductionStatus.INTRODUCED}

    # I1: central validation of transitions. It rejects any state change not allowed by the lifecycle.
    def _validate_transition(self, new_status: str) -> None:
        if self.pk is None:
            return

        previous_status = self.__class__.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        if previous_status is None:
            return

        allowed = self.ALLOWED_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed:
            raise InvalidTransition(current_status=previous_status, next_status=new_status)

    # I1: defensive check. A direct save cannot bypass the lifecycle rules.
    def save(self, *args, **kwargs):
        if self.pk:
            current_status = self.__class__.objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if current_status and current_status != self.status:
                self._validate_transition(self.status)
        super().save(*args, **kwargs)

    @property
    def can_respond(self):
        if self.status != IntroductionStatus.INTERESTED:
            return False
        if self.expires_at is None:
            return True
        return timezone.now() <= self.expires_at

    def __str__(self) -> str:
        return f"{self.startup_id} -> {self.investor_id} [{self.status}]"


# I2: investor consent journal for the "startup notification" wording.
# This records the exact legal text version the investor accepted before the startup is notified.
class IntroductionConsent(models.Model):
    introduction = models.ForeignKey(
        "Introduction",
        on_delete=models.CASCADE,
        related_name="consents",
    )
    text_version = models.CharField(max_length=80, default=INTRO_NOTICE_TEXT_VERSION)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accepted_at"]


# I4: startup decision log. It captures who approved or rejected the introduction, with which version of text D.
class StartupIntroDecisionLog(models.Model):
    DECISION_FREIGABE = "freigabe"
    DECISION_NEIN = "nein"
    DECISION_CHOICES = [
        (DECISION_FREIGABE, "Freigabe"),
        (DECISION_NEIN, "Nein"),
    ]

    introduction = models.ForeignKey("Introduction", on_delete=models.CASCADE, related_name="startup_decisions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_intro_decisions")
    decision = models.CharField(max_length=16, choices=DECISION_CHOICES)
    text_version = models.CharField(max_length=80, default="intro-request-v1")
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]


# I3: idempotent delivery journal for startup request emails.
# One intro request should produce one email even if the task or endpoint is retried.
class IntroductionEmailLog(models.Model):
    introduction = models.ForeignKey(
        "Introduction",
        on_delete=models.CASCADE,
        related_name="email_logs",
    )
    channel = models.CharField(max_length=32, default="startup_interest")
    recipient = models.EmailField(blank=True, default="")
    provider = models.CharField(max_length=64, default="default")
    subject = models.CharField(max_length=255, blank=True, default="")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["introduction", "channel"], name="uniq_intro_email_channel"),
        ]
        ordering = ["-sent_at"]


# I1 + I2: domain service that owns all status transitions and investor reactions.
# This is the only place where state changes are allowed, which prevents race conditions and invalid transitions.
class IntroductionService:
    """Domain service for safe status transitions."""

    @staticmethod
    def _locked(introduction_id: int) -> Introduction:
        return (
            Introduction.objects.select_for_update()
            .select_related("startup", "investor")
            .get(pk=introduction_id)
        )

    # I2: investor note validation. The startup sees the note, but no email/URL/phone data is allowed.
    @staticmethod
    def assert_provider_allowed(provider_name: str = "default") -> None:
        # I3: fail-closed provider check. Real email sending is disabled unless the provider is explicitly permitted.
        assert_provider_allowed(provider_name)

    @staticmethod
    def _validate_message(message: str | None) -> str:
        if message is None:
            return ""
        text = message.strip()
        if len(text) > 280:
            raise ValidationError("investor_message must be under 280 characters.")
        if any(token in text.lower() for token in ("@", "http://", "https://", "/")):
            raise ValidationError("Investor message cannot contain email, URL, or phone-like data.")
        return text

    @staticmethod
    def normalize_decline_reason(reason: str | None) -> str:
        normalized = (reason or "").strip().lower()
        if not normalized:
            return ""
        if normalized not in DECLINE_REASONS:
            raise ValidationError("Unsupported decline reason.")
        return DECLINE_REASONS[normalized]

    # I2: investor clicks "Interested" and opens the intro request.
    # This transition is allowed only from SUGGESTED and only when the investor confirms the notice.
    @classmethod
    def interest(
        cls,
        introduction: Introduction,
        investor_message: str | None = None,
        *,
        notification_accepted: bool = False,
        text_version: str = INTRO_NOTICE_TEXT_VERSION,
        now=None,
    ):
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.SUGGESTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.INTERESTED)
            if not notification_accepted:
                raise ValidationError("Investor notification confirmation is required.")
            intro.investor_message = cls._validate_message(investor_message)
            intro.status = IntroductionStatus.INTERESTED
            intro.interested_at = now
            intro.expires_at = now + timedelta(days=getattr(settings, "INTRO_EXPIRE_DAYS", 7))
            intro.save(update_fields=["status", "interested_at", "expires_at", "investor_message"])
            IntroductionConsent.objects.update_or_create(
                introduction=intro,
                defaults={"text_version": text_version},
            )
            EventLog.objects.create(
                event_type=EventLog.EVENT_INTERESTED,
                startup=intro.startup,
                investor=intro.investor,
                payload={"has_message": bool(intro.investor_message)},
            )
            cls.notify_startup_of_interest(intro)
            return intro

    # I2: investor closes the introduction with a reason from the approved list.
    @classmethod
    def decline_by_investor(cls, introduction: Introduction, reason: str | None = None, *, now=None):
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.SUGGESTED and intro.status != IntroductionStatus.INTERESTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.DECLINED)
            intro.decline_reason = cls.normalize_decline_reason(reason) if reason else ""
            intro.status = IntroductionStatus.DECLINED
            intro.expires_at = now
            intro.save(update_fields=["status", "expires_at", "decline_reason"])
            EventLog.objects.create(
                event_type=EventLog.EVENT_DECLINED,
                startup=intro.startup,
                investor=intro.investor,
                payload={"reason": intro.decline_reason or None},
            )
            return intro

    @classmethod
    def notify_startup_of_interest(cls, introduction: Introduction, *, now=None):
        # I3: startup request email. It must be sent once per intro even if the task is retried.
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.INTERESTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.INTERESTED)
            cls.assert_provider_allowed("startup-interest-email")
            recipient = getattr(intro.startup, "contact_email", "") or ""
            if not recipient:
                raise ValidationError("Startup contact email is required to send the intro request.")
            if IntroductionEmailLog.objects.filter(introduction=intro, channel="startup_interest").exists():
                return intro
            investor_name = getattr(intro.investor, "organization_name", "") or getattr(intro.investor, "name", "Investor")
            investor_type = getattr(intro.investor, "organization_type", "Fund") or "Fund"
            subject = "Neues Interesse für Ihr Startup"
            message = (
                f"{investor_name} ({investor_type}) hat Interesse an Ihrem Profil.\n\n"
                "Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben.\n"
                "Bitte antworten Sie im Dashboard der Plattform, nicht per E-Mail."
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                recipient_list=[recipient],
                fail_silently=False,
            )
            IntroductionEmailLog.objects.create(
                introduction=intro,
                channel="startup_interest",
                recipient=recipient,
                provider=getattr(settings, "INTRO_EMAIL_PROVIDER", "default"),
                subject=subject,
            )
            intro.reminder_sent_at = now
            intro.save(update_fields=["reminder_sent_at"])
            return intro

    @classmethod
    def send_intro(cls, introduction_id: int):
        # I5: send intro contact emails to both parties. This task is idempotent and only sends missing side emails.
        intro = Introduction.objects.select_related("startup", "investor", "startup__owner", "investor__owner").get(pk=introduction_id)
        if intro.status != IntroductionStatus.ACCEPTED:
            return False
        if intro.startup.profile_status == "REMOVED":
            return False
        if intro.startup.owner is None or intro.investor.owner is None:
            return False

        cls.assert_provider_allowed("intro-email")

        startup_email = getattr(intro.startup.owner, "email", "") or intro.startup.contact_email or ""
        investor_email = getattr(intro.investor.owner, "email", "") or intro.investor.contact_email or ""
        if not startup_email or not investor_email:
            return False

        if not intro.sent_to_startup:
            with transaction.atomic():
                intro = cls._locked(intro.pk)
                if intro.sent_to_startup:
                    return False
                startup_contact = intro.startup.contact_name or intro.startup.company_name or getattr(intro.startup.owner, "first_name", "") or "Startup"
                subject = "Kontaktfreigabe für Ihr Startup"
                body = (
                    f"Hallo {startup_contact},\n\n"
                    f"{intro.investor.organization_name or intro.investor.name or 'Investor'} hat Ihre Kontaktdaten freigegeben.\n"
                    f"Kontakt: {intro.investor.contact_name or intro.investor.name or 'Kontakt'}\n"
                    f"E-Mail: {investor_email}\n"
                    f"Organisation: {intro.investor.organization_name or intro.investor.name or 'Investor'}\n\n"
                    f"{INTRO_EMAIL_TEXT}"
                )
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [startup_email], fail_silently=False)
                IntroductionEmailLog.objects.create(
                    introduction=intro,
                    channel="startup_intro_email",
                    recipient=startup_email,
                    provider=getattr(settings, "INTRO_EMAIL_PROVIDER", "default"),
                    subject=subject,
                )
                intro.sent_to_startup = True
                intro.save(update_fields=["sent_to_startup"])

        if not intro.sent_to_investor:
            with transaction.atomic():
                intro = cls._locked(intro.pk)
                if intro.sent_to_investor:
                    return False
                investor_contact = intro.investor.contact_name or intro.investor.name or "Investor"
                subject = "Kontaktfreigabe für Ihren Investor"
                body = (
                    f"Hallo {investor_contact},\n\n"
                    f"{intro.startup.company_name or intro.startup.name or 'Startup'} hat Ihre Kontaktdaten freigegeben.\n"
                    f"Kontakt: {intro.startup.contact_name or intro.startup.company_name or 'Kontakt'}\n"
                    f"E-Mail: {startup_email}\n"
                    f"Organisation: {intro.startup.company_name or intro.startup.name or 'Startup'}\n\n"
                    f"{INTRO_EMAIL_TEXT}"
                )
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [investor_email], fail_silently=False)
                IntroductionEmailLog.objects.create(
                    introduction=intro,
                    channel="investor_intro_email",
                    recipient=investor_email,
                    provider=getattr(settings, "INTRO_EMAIL_PROVIDER", "default"),
                    subject=subject,
                )
                intro.sent_to_investor = True
                intro.save(update_fields=["sent_to_investor"])

        if intro.sent_to_startup and intro.sent_to_investor and intro.status == IntroductionStatus.ACCEPTED:
            with transaction.atomic():
                intro = cls._locked(intro.pk)
                if intro.status != IntroductionStatus.ACCEPTED:
                    return False
                intro.status = IntroductionStatus.INTRODUCED
                intro.save(update_fields=["status"])
                EventLog.objects.create(
                    event_type=EventLog.EVENT_STATUS_CHANGED,
                    startup=intro.startup,
                    investor=intro.investor,
                    payload={
                        "previous_status": IntroductionStatus.ACCEPTED,
                        "new_status": IntroductionStatus.INTRODUCED,
                        "message": "intro_emails_sent",
                    },
                )
        return True

    @classmethod
    def accept(cls, introduction: Introduction, *, now=None, user=None, text_version="intro-request-v1"):
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.INTERESTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.ACCEPTED)
            previous_status = intro.status
            intro.status = IntroductionStatus.ACCEPTED
            intro.expires_at = now
            intro.save(update_fields=["status", "expires_at"])
            EventLog.objects.create(
                event_type=EventLog.EVENT_STATUS_CHANGED,
                startup=intro.startup,
                investor=intro.investor,
                payload={
                    "previous_status": previous_status,
                    "new_status": IntroductionStatus.ACCEPTED,
                    "response_time_seconds": (now - intro.interested_at).total_seconds() if intro.interested_at else 0,
                    "decision": "freigabe",
                },
            )
            if user is not None:
                StartupIntroDecisionLog.objects.create(
                    introduction=intro,
                    user=user,
                    decision=StartupIntroDecisionLog.DECISION_FREIGABE,
                    text_version=text_version,
                )
            transaction.on_commit(lambda: cls.send_intro(intro.pk))
            return intro

    @classmethod
    def decline_by_startup(cls, introduction: Introduction, *, now=None, user=None, text_version="intro-request-v1"):
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.INTERESTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.DECLINED)
            previous_status = intro.status
            intro.status = IntroductionStatus.DECLINED
            intro.expires_at = now
            intro.save(update_fields=["status", "expires_at"])
            EventLog.objects.create(
                event_type=EventLog.EVENT_STATUS_CHANGED,
                startup=intro.startup,
                investor=intro.investor,
                payload={
                    "previous_status": previous_status,
                    "new_status": IntroductionStatus.DECLINED,
                    "response_time_seconds": (now - intro.interested_at).total_seconds() if intro.interested_at else 0,
                    "decision": "nein",
                },
            )
            if user is not None:
                StartupIntroDecisionLog.objects.create(
                    introduction=intro,
                    user=user,
                    decision=StartupIntroDecisionLog.DECISION_NEIN,
                    text_version=text_version,
                )
            return intro

    @classmethod
    def expire(cls, introduction: Introduction | int, *, now=None):
        now = now or timezone.now()
        intro_obj = introduction if isinstance(introduction, Introduction) else Introduction.objects.get(pk=introduction)
        with transaction.atomic():
            intro = cls._locked(intro_obj.pk)
            previous_status = intro.status
            if intro.status not in {IntroductionStatus.SUGGESTED, IntroductionStatus.INTERESTED}:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.EXPIRED)
            intro.status = IntroductionStatus.EXPIRED
            intro.expires_at = now
            intro.save(update_fields=["status", "expires_at"])
            EventLog.objects.create(
                event_type=EventLog.EVENT_STATUS_CHANGED,
                startup=intro.startup,
                investor=intro.investor,
                payload={
                    "previous_status": previous_status,
                    "new_status": IntroductionStatus.EXPIRED,
                    "reason": "expired",
                },
            )
            return intro

    @staticmethod
    def can_send_sms(*, provider_allowed=None, provider_name: str = "default") -> bool:
        if provider_allowed is not None:
            return bool(provider_allowed)
        if getattr(settings, "INTRO_SMS_PROVIDER_ALLOWED", False):
            return True
        return False

    @classmethod
    def send_reminder_if_due(cls, introduction_id: int, *, now=None):
        now = now or timezone.now()
        introduction = Introduction.objects.select_related("startup", "investor").get(pk=introduction_id)
        if introduction.status != IntroductionStatus.INTERESTED or introduction.reminder_sent_at is not None:
            return False
        if not getattr(settings, "INTRO_EMAIL_PROVIDER_ALLOWED", True):
            raise ValidationError("Email provider is not allowed in the current environment.")
        recipient = getattr(introduction.startup, "contact_email", "") or ""
        if not recipient:
            return False
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.INTERESTED or intro.reminder_sent_at is not None:
                return False
            cls.assert_provider_allowed("startup-interest-reminder")
            send_mail(
                subject="Erinnerung: Antwort auf Ihr Intro-Angebot",
                message=(
                    f"Hallo {intro.startup.company_name or intro.startup.name or 'Startup'},\n\n"
                    f"Ihre Antwort auf die Anfrage von {intro.investor.organization_name or intro.investor.name or 'Investor'} "
                    f"ist noch ausstehend. Bitte prüfen Sie die Anfrage im Dashboard."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                recipient_list=[recipient],
                fail_silently=False,
            )
            intro.reminder_sent_at = now
            intro.save(update_fields=["reminder_sent_at"])
            return True

    @classmethod
    def expire_overdue(cls, *, now=None):
        # I6: close any INTERESTED introductions whose deadline has passed.
        # This runs as a periodic job, is idempotent, and leaves the flow in EXPIRED without extending the deadline.
        now = now or timezone.now()
        expired_ids = []
        for intro in Introduction.objects.filter(status=IntroductionStatus.INTERESTED, expires_at__lt=now).select_related("startup", "investor"):
            with transaction.atomic():
                current = cls._locked(intro.pk)
                if current.status != IntroductionStatus.INTERESTED:
                    continue
                previous_status = current.status
                current.status = IntroductionStatus.EXPIRED
                current.expires_at = now
                current.save(update_fields=["status", "expires_at"])
                EventLog.objects.create(
                    event_type=EventLog.EVENT_STATUS_CHANGED,
                    startup=current.startup,
                    investor=current.investor,
                    payload={
                        "previous_status": previous_status,
                        "new_status": IntroductionStatus.EXPIRED,
                        "reason": "expired",
                    },
                )
                expired_ids.append(current.pk)
        return expired_ids

    @classmethod
    def send_due_reminders(cls, *, now=None, channel=None):
        # I6: one reminder per introduction before the deadline. A reminder is sent only once and only while the intro remains INTERESTED.
        now = now or timezone.now()
        reminder_days = int(getattr(settings, "INTRO_REMINDER_DAYS", 4))
        selected_channel = channel or getattr(settings, "INTRO_REMINDER_CHANNEL", "email")
        sent_ids = []
        cutoff = now - timedelta(days=reminder_days)
        for intro in (
            Introduction.objects.filter(
                status=IntroductionStatus.INTERESTED,
                interested_at__lte=cutoff,
                reminder_sent_at__isnull=True,
            )
            .select_related("startup", "investor")
        ):
            with transaction.atomic():
                current = cls._locked(intro.pk)
                if current.status != IntroductionStatus.INTERESTED or current.reminder_sent_at is not None:
                    continue
                if selected_channel == "sms":
                    if not getattr(settings, "INTRO_SMS_PROVIDER_ALLOWED", False):
                        raise ValidationError("SMS reminder provider is not allowed in the current environment.")
                else:
                    cls.assert_provider_allowed("startup-interest-reminder")
                recipient = getattr(current.startup, "contact_email", "") or ""
                if not recipient:
                    continue
                subject = "Erinnerung: Antwort auf Ihr Intro-Angebot"
                message = (
                    f"Hallo {current.startup.company_name or current.startup.name or 'Startup'},\n\n"
                    f"Ihre Antwort auf die Anfrage von {current.investor.organization_name or current.investor.name or 'Investor'} "
                    f"ist noch ausstehend. Bitte prüfen Sie die Anfrage im Dashboard."
                )
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                current.reminder_sent_at = now
                current.save(update_fields=["reminder_sent_at"])
                sent_ids.append(current.pk)
        return sent_ids

    @classmethod
    def close_inactive_cards(cls, *, now=None):
        # I6: this is a separate list-management task; it does not change the intro status, it only exposes stale cards as inactive.
        now = now or timezone.now()
        active_days = int(getattr(settings, "CARD_ACTIVE_DAYS", 30))
        cutoff = now - timedelta(days=active_days)
        return list(
            Introduction.objects.filter(
                status=IntroductionStatus.INTERESTED,
                interested_at__lte=cutoff,
            )
            .values_list("pk", flat=True)
        )

    @classmethod
    def close_startup_intros_on_profile_status_change(cls, startup, *, now=None):
        # I7: if a startup pauses or removes its profile, all open interest requests are closed immediately.
        # We keep the legal and privacy behavior fail-closed: no company is contacted after profile shutdown.
        now = now or timezone.now()
        with transaction.atomic():
            introductions = list(
                Introduction.objects.filter(startup=startup, status=IntroductionStatus.INTERESTED)
                .select_related("startup", "investor")
            )
            closed = []
            for intro in introductions:
                current = cls._locked(intro.pk)
                previous_status = current.status
                if current.status != IntroductionStatus.INTERESTED:
                    continue
                current.status = IntroductionStatus.EXPIRED
                current.expires_at = now
                current.save(update_fields=["status", "expires_at"])
                EventLog.objects.create(
                    event_type=EventLog.EVENT_STATUS_CHANGED,
                    startup=current.startup,
                    investor=current.investor,
                    payload={
                        "previous_status": previous_status,
                        "new_status": IntroductionStatus.EXPIRED,
                        "reason": "startup_profile_paused_or_removed",
                    },
                )
                investor_email = getattr(current.investor.owner, "email", "") or current.investor.contact_email or ""
                if investor_email:
                    send_mail(
                        subject="Startup pausiert oder entfernt Profil",
                        message=(
                            "Das Startup, mit dem Sie ein Intro gestartet haben, ist derzeit nicht mehr aktiv. "
                            "Es sucht aktuell keinen Investor mehr."
                        ),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                        recipient_list=[investor_email],
                        fail_silently=False,
                    )
                closed.append(current.pk)
            return closed

    @classmethod
    def remove_investor_open_intros(cls, investor, *, now=None):
        # I7: deleting an investor profile must remove active intro requests without sending a message back to the startup.
        now = now or timezone.now()
        with transaction.atomic():
            introductions = list(
                Introduction.objects.filter(investor=investor, status__in=[IntroductionStatus.INTERESTED, IntroductionStatus.ACCEPTED])
                .select_related("startup", "investor")
            )
            removed = []
            for intro in introductions:
                current = cls._locked(intro.pk)
                removed.append(current.pk)
                EventLog.objects.create(
                    event_type=EventLog.EVENT_STATUS_CHANGED,
                    startup=current.startup,
                    investor=current.investor,
                    payload={
                        "previous_status": current.status,
                        "new_status": "DELETED",
                        "reason": "investor_account_removed",
                    },
                )
                current.delete()
            return removed

    @classmethod
    def mark_introduced(cls, introduction: Introduction, *, now=None):
        now = now or timezone.now()
        with transaction.atomic():
            intro = cls._locked(introduction.pk)
            if intro.status != IntroductionStatus.ACCEPTED:
                raise InvalidTransition(current_status=intro.status, next_status=IntroductionStatus.INTRODUCED)
            intro.status = IntroductionStatus.INTRODUCED
            intro.expires_at = now
            intro.save(update_fields=["status", "expires_at"])
            return intro
