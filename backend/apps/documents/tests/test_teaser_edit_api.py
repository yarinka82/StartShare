
"""API-тесты редактирования и затверждения. python manage.py test apps.documents.tests.test_teaser_edit_api"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.analytics.models import Event
from apps.documents.models import PitchDeck, Teaser, TeaserJob
from apps.documents.teaser.contract import FIELD_NAMES
from apps.profiles.models import StartupProfile

TEXT = {
    "headline": "Software fuer die ambulante Pflege",
    "problem": "Dokumentation kostet Zeit.",
    "solution": "Eine Cloud-Loesung spart Papier.",
    "market": "",
    "traction": "Pilot mit einem grossen Klinikverbund.",
    "team": "Erfahrenes Team.",
}
NONEMPTY = [f for f in FIELD_NAMES if TEXT[f]]
LLM_PHRASE = {"category_id": "R09", "field": "traction", "quote": "einem grossen Klinikverbund",
              "action": "highlight", "reason": "customer", "source": "llm", "start": 11, "end": 38}


def make_user(name: str):
    user = get_user_model().objects.create_user(
        email=f"{name}@example.com",
        password="x",
        role="startup",
    )
    profile, _ = StartupProfile.objects.get_or_create(
        user=user,
        defaults={
            "team_size": 1,
            "company_name": "Lumora",  # <-- Додаємо назву компанії для перевірки правила R01
        },
    )
    # Якщо профіль вже існував без назви — оновлюємо
    if not profile.company_name:
        profile.company_name = "Lumora"
        profile.save()
    
    return user


class TeaserEditTests(TestCase):
    def setUp(self):
        self.user = make_user("anna")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.deck, self.job = self.make_job(self.user)
        self.url = f"/api/decks/{self.deck.id}/teaser/"

    def make_job(self, user, state=TeaserJob.State.DRAFT_READY):
        user = user or self.user
        profile = StartupProfile.objects.get(user=user)
        deck = PitchDeck.objects.create(startup=profile, file="decks/x.pdf")
        job = TeaserJob.objects.create(
            deck=deck, state=state, draft={"teaser": dict(TEXT), "language": "de"} if state == "DRAFT_READY" else None,
            risk_phrases=[dict(LLM_PHRASE)] if state == "DRAFT_READY" else [])
        return deck, job

    def edit(self, **fields):
        return self.client.patch(self.url, {"fields": fields}, format="json")

    def review(self, *fields):
        return self.client.post(self.url + "review/", {"fields": list(fields)}, format="json")

    def approve(self, declaration=True):
        return self.client.post(self.url + "approve/", {"declaration_a": declaration}, format="json")

    def events(self, name):
        return Event.objects.filter(name=name)

    # --- чтение ---
    def test_get_creates_working_copy_from_draft(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["content"], TEXT)
        self.assertEqual(r.data["status"], "DRAFT")
        self.assertEqual(r.data["reviewed"], [])
        self.assertEqual(r["Cache-Control"], "no-store")
        codes = {(b["field"], b["code"]) for b in r.data["approval_blockers"]}
        self.assertEqual(codes, {(f, "not_reviewed") for f in NONEMPTY})
        self.assertEqual(Teaser.objects.count(), 1)

    def test_repeated_get_does_not_duplicate(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertEqual(Teaser.objects.count(), 1)

    def test_draft_not_ready_is_409(self):
        deck, _ = self.make_job(make_user("boris"), state=TeaserJob.State.PROCESSING)
        c = APIClient()
        c.force_authenticate(deck.startup.user)
        self.assertEqual(c.get(f"/api/decks/{deck.id}/teaser/").status_code, 409)

    def test_other_user_404_and_anonymous_denied(self):
        c = APIClient()
        c.force_authenticate(make_user("boris"))
        self.assertEqual(c.get(self.url).status_code, 404)
        self.assertEqual(c.patch(self.url, {"fields": {"team": "x"}}, format="json").status_code, 404)
        self.assertIn(APIClient().get(self.url).status_code, (401, 403))

    # --- правка ---
    def test_edit_changes_content_resets_review_logs_field_name_only(self):
        self.review("headline", "problem")
        r = self.edit(problem="Dokumentation frisst Pflegezeit.")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["content"]["problem"], "Dokumentation frisst Pflegezeit.")
        self.assertEqual(r.data["reviewed"], ["headline"])           # только изменённое поле потеряло подтверждение
        (ev,) = self.events("field_edited")
        self.assertEqual(ev.properties, {"field": "problem"})        # без текста
        self.job.refresh_from_db()
        self.assertEqual(self.job.draft["teaser"]["problem"], TEXT["problem"])  # исходный вывод ШІ не тронут

    def test_edit_same_value_is_noop(self):
        self.review("problem")
        r = self.edit(problem="  " + TEXT["problem"] + " ")
        self.assertEqual(r.data["reviewed"], ["problem"])
        self.assertEqual(self.events("field_edited").count(), 0)

    def test_edit_can_fill_optional_field(self):
        r = self.edit(market="Ambulante Pflegedienste in DACH.")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["content"]["market"], "Ambulante Pflegedienste in DACH.")

    def test_edit_validation(self):
        for body in ({"nope": "x"}, {"headline": ""}, {"headline": "x" * 201}, {"headline": 5},
                     {"problem": "Mail [REDACTED_EMAIL]"}):
            r = self.edit(**body)
            self.assertEqual(r.status_code, 400, body)
        self.assertEqual(self.client.patch(self.url, {"fields": {}}, format="json").status_code, 400)
        self.assertEqual(self.events("field_edited").count(), 0)
        self.assertEqual(self.client.get(self.url).data["content"], TEXT)

    # --- risk_phrases после правки ---
    def test_llm_phrase_kept_with_new_offsets_or_dropped(self):
        r = self.edit(traction="Heute: Pilot mit einem grossen Klinikverbund.")
        (p,) = r.data["risk_phrases"]
        txt = r.data["content"]["traction"]
        self.assertEqual(txt[p["start"]:p["end"]], "einem grossen Klinikverbund")
        r = self.edit(traction="Pilot mit einem Kunden.")
        self.assertEqual(r.data["risk_phrases"], [])

    def test_typed_email_is_flagged_blocks_review_and_clears_after_fix(self):
        r = self.edit(team="Kontakt: anna@lumora-beispiel.de")
        flags = [(p["field"], p["category_id"], p["source"]) for p in r.data["risk_phrases"]]
        self.assertIn(("team", "R04", "regex"), flags)
        bad = self.review("team")
        self.assertEqual((bad.status_code, bad.data["fields"]["team"]), (400, "risk_found"))
        self.edit(team="Erfahrenes Team.")
        self.assertEqual(self.review("team").status_code, 200)

    def test_company_name_typed_by_user_is_flagged(self):
        r = self.edit(headline="Lumora baut Pflegesoftware")
        self.assertIn(("headline", "R01", "leak"),
                      [(p["field"], p["category_id"], p["source"]) for p in r.data["risk_phrases"]])

    # --- подтверждение полей ---
    def test_review_rules(self):
        self.assertEqual(self.review("bogus").status_code, 400)
        self.assertEqual(self.client.post(self.url + "review/", {"fields": []}, format="json").status_code, 400)
        empty = self.review("market")
        self.assertEqual((empty.status_code, empty.data["fields"]["market"]), (400, "empty_field"))
        ok = self.review("headline", "problem")
        self.assertEqual(ok.data["reviewed"], ["headline", "problem"])
        self.assertEqual(self.review("problem").data["reviewed"], ["headline", "problem"])  # идемпотентно

    def test_review_is_all_or_nothing(self):
        self.edit(team="Mail anna@lumora-beispiel.de")
        self.assertEqual(self.review("headline", "team").status_code, 400)
        self.assertEqual(self.client.get(self.url).data["reviewed"], [])

    # --- затверждение ---
    def test_approve_requires_declaration(self):
        self.review(*NONEMPTY)
        for decl in (False, None, "true", 1):
            self.assertEqual(self.approve(decl).status_code, 400)
        self.assertEqual(Teaser.objects.get().status, "DRAFT")

    def test_approve_blocked_until_all_fields_reviewed(self):
        self.review("headline")
        r = self.approve()
        self.assertEqual(r.status_code, 400)
        missing = {b["field"] for b in r.data["blockers"] if b["code"] == "not_reviewed"}
        self.assertEqual(missing, set(NONEMPTY) - {"headline"})

    def test_full_flow_approve_lock_and_idempotency(self):
        self.review(*NONEMPTY)
        r = self.approve()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "APPROVED")
        self.assertIsNotNone(r.data["approved_at"])
        self.assertIsNotNone(r.data["declaration_a_accepted_at"])
        self.assertEqual(self.events("teaser_approved").count(), 1)

        again = self.approve()                                       # повтор: 200 и без нового события
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self.events("teaser_approved").count(), 1)

        self.assertEqual(self.edit(team="Neu").status_code, 409)     # после затверждения всё заперто
        self.assertEqual(self.review("team").status_code, 409)
        self.assertEqual(self.client.get(self.url).data["content"], TEXT)

    def test_edit_after_review_requires_rereview_before_approval(self):
        self.review(*NONEMPTY)
        self.edit(team="Ein kleines Team.")
        r = self.approve()
        self.assertEqual(r.status_code, 400)
        self.assertEqual([(b["field"], b["code"]) for b in r.data["blockers"]], [("team", "not_reviewed")])

    def test_approve_blocked_if_company_name_changes_after_review(self):
        self.review(*NONEMPTY)
        profile = StartupProfile.objects.get(user=self.user)
        profile.company_name = "Klinikverbund"                       # теперь это слово есть в тексте traction
        profile.save()
        self.edit(team="Erfahrenes Team, jetzt staerker.")           # правка пересчитывает проверки
        self.review("team")
        self.edit(traction="Pilot mit einem grossen Klinikverbund!") # traction теперь содержит внутреннее название
        r = self.approve()
        self.assertEqual(r.status_code, 400)
        self.assertIn(("traction", "risk_found"), [(b["field"], b["code"]) for b in r.data["blockers"]])