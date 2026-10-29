
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    Language,
    LegalDocument,
    LegalDocumentCode,
    User,
    UserConsent,
    UserConsentContext,
    UserRole,
)
from apps.startups.models import (
    BusinessModel,
    Country,
    Sector,
    Stage,
    StartupProfile,
)
from apps.documents.models import PitchDeck, Teaser, TeaserField


STARTUPS_DATA = [
    {
        "email": "startup_pflege@test.de",
        "company_name": "PflegeFlow Technologies",
        "sector_code": "b2b-saas",
        "sector_name": "B2B SaaS / Enterprise",
        "stage_code": "seed",
        "stage_name": "Seed",
        "country_code": "de",
        "country_name": "Germany",
        "bm_code": "saas-subscription",
        "bm_name": "SaaS & Subscription",
        "round_amount_eur": Decimal("1200000"),
        "mrr_eur": Decimal("47200"),
        "team_size": 9,
        "teaser": {
            "headline": "SaaS-Plattform für automatisierte Pflegedokumentation im DACH-Raum",
            "problem": "Pflegekräfte in ambulanten Diensten verbringen über 30 % ihrer Zeit mit bürokratischer Dokumentation und fehleranfälliger Abrechnung.",
            "solution": "Sprachgestützte Tablet-Anwendung mit Offline-Modus und automatischer Plausibilitätsprüfung für Krankenkassenabrechnungen.",
            "market": "Rund 15.000 ambulante Pflegedienste in Deutschland mit einem adressierbaren Markt von 1,4 Mrd. EUR.",
            "traction": "47.200 EUR MRR mit 312 zahlenden B2B-Kunden. Zweistelliges monatliches Wachstum und erfolgreicher Klinikpilot.",
            "team": "Gegründet von einer erfahrenen HealthTech-Führungskraft und einem Cloud-Architekten mit 8 Jahren Branchenerfahrung.",
        },
    },
    {
        "email": "startup_logi@test.de",
        "company_name": "LogiChain Intelligence",
        "sector_code": "ai-data",
        "sector_name": "AI & Data Infrastructure",
        "stage_code": "seed",
        "stage_name": "Seed",
        "country_code": "de",
        "country_name": "Germany",
        "bm_code": "saas-subscription",
        "bm_name": "SaaS & Subscription",
        "round_amount_eur": Decimal("1500000"),
        "mrr_eur": Decimal("35000"),
        "team_size": 6,
        "teaser": {
            "headline": "KI-gestützte Lieferketten-Vorhersage für den deutschen Mittelstand",
            "problem": "Unerwartete Lieferengpässe und Transportverzögerungen kosten mittelständische Fertigungsbetriebe bis zu 12 % ihrer Marge.",
            "solution": "Prädiktive Analyse-Software, die bestehende ERP-Systeme binnen 48 Stunden anbindet und Lieferausfälle 14 Tage im Voraus prognostiziert.",
            "market": "Über 40.000 produzierende Betriebe in Deutschland, Österreich und der Schweiz.",
            "traction": "18 aktive Industrie-Kunden, 35.000 EUR MRR, 15 % MoM-Wachstum, POC mit Tier-1 Zulieferer.",
            "team": "Team aus ehemaligen Supply-Chain-Leads eines großen Technologiekonzerns und Universitäts-Forschern.",
        },
    },
    {
        "email": "startup_tax@test.de",
        "company_name": "TaxPayroll DACH",
        "sector_code": "fintech",
        "sector_name": "FinTech / InsurTech",
        "stage_code": "pre-seed",
        "stage_name": "Pre-Seed",
        "country_code": "at",
        "country_name": "Austria",
        "bm_code": "transaction-fee",
        "bm_name": "Transactional / Fee",
        "round_amount_eur": Decimal("600000"),
        "mrr_eur": Decimal("12500"),
        "team_size": 4,
        "teaser": {
            "headline": "Automatisierte grenzüberschreitende Gehaltsabrechnung im DACH-Raum",
            "problem": "Unternehmen mit Mitarbeitern in Deutschland, Österreich und der Schweiz scheitern an komplexen länderspezifischen Steuervorschriften.",
            "solution": "API-first Payroll-Infrastruktur, die Lohnabrechnung, Sozialabgaben und Quellensteuern vollautomatisch gesetzeskonform abwickelt.",
            "market": "Wachsender Markt für Remote-First Unternehmen im DACH-Raum mit über 500 Mio. EUR Payroll-Volumen.",
            "traction": "12.500 EUR MRR in 5 Monaten nach Launch, über 45 Firmenkunden, Partnerschaft mit Steuerberatungsgesellschaft.",
            "team": "Zwei Seriengründer mit FinTech- und RegTech-Exits und erfahrener Fachanwalt für Steuerrecht.",
        },
    },
    {
        "email": "startup_solar@test.de",
        "company_name": "CleanGrid Systems",
        "sector_code": "climatetech",
        "sector_name": "ClimateTech / CleanTech",
        "stage_code": "seed",
        "stage_name": "Seed",
        "country_code": "ch",
        "country_name": "Switzerland",
        "bm_code": "saas-subscription",
        "bm_name": "SaaS & Subscription",
        "round_amount_eur": Decimal("2000000"),
        "mrr_eur": Decimal("62000"),
        "team_size": 11,
        "teaser": {
            "headline": "Intelligente Einspeiseoptimierung für gewerbliche Photovoltaik-Großanlagen",
            "problem": "Betreiber von Industrie-Solaranlagen verlieren durch ungenutzte Einspeisespitzen und starre Netzentgelte erhebliche Erträge.",
            "solution": "IoT- und Softwarelösung zur dynamischen Steuerung von Großbatterien und Spitzenlasten für Gewerbeimmobilien.",
            "market": "Europäischer Markt für Gewerbe-PV mit über 25 GW installierter Leistung.",
            "traction": "62.000 EUR MRR, 28 Gewerbeparks unter Vertrag, zertifizierte Schnittstellen zu allen großen Verteilnetzbetreibern.",
            "team": "Führungsteam aus Energiewirtschafts-Experten und IoT-Hardware-Ingenieuren der ETH Zürich.",
        },
    },
    {
        "email": "startup_cyber@test.de",
        "company_name": "NIS2 Guard",
        "sector_code": "cybersecurity",
        "sector_name": "Cybersecurity",
        "stage_code": "pre-seed",
        "stage_name": "Pre-Seed",
        "country_code": "de",
        "country_name": "Germany",
        "bm_code": "saas-subscription",
        "bm_name": "SaaS & Subscription",
        "round_amount_eur": Decimal("750000"),
        "mrr_eur": Decimal("18000"),
        "team_size": 5,
        "teaser": {
            "headline": "Automatisierte NIS-2 Compliance und Schwachstellen-Scanning für den Mittelstand",
            "problem": "Tausende Unternehmen müssen die neue europäische NIS-2 Richtlinie umsetzen, verfügen jedoch über keine eigene Security-Abteilung.",
            "solution": "Agentenloses Continuous-Monitoring-Tool, das Compliance-Lücken aufdeckt und auditfeste Berichte auf Knopfdruck generiert.",
            "market": "Allein in Deutschland sind über 30.000 mittelständische Unternehmen direkt von der NIS-2 Regulierung betroffen.",
            "traction": "18.000 EUR MRR, 65 aktive Mandanten, Kooperation mit regionalen IT-Systemhäusern.",
            "team": "Ehemalige Pentester und IT-Sicherheitsberater für kritische Infrastrukturen.",
        },
    },
]


class Command(BaseCommand):
    help = "Наповнює базу 5 тестовими стартапами у статусі LIVE під нову схему БД"

    def add_arguments(self, parser):
        parser.add_argument(
            "--digest",
            action="store_true",
            help="Одразу згенерувати тижневий дайджест для інвесторів після створення стартапів",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        created_count = 0

        # Документ Декларації A
        doc_a, _ = LegalDocument.objects.get_or_create(
            code=getattr(LegalDocumentCode, "A", "A"),
            language="de",
            defaults={
                "version": 1,
                "title": "Erklärung des Startups",
                "body": "Ich bestätige, dass die Angaben nach bestem Wissen richtig sind...",
                "legal_approved_at": now,
                "valid_from": now,
            },
        )

        for data in STARTUPS_DATA:
            #  Створюємо довідники в БД (Sector, Stage, BusinessModel, Country)
            sector, _ = Sector.objects.get_or_create(
                code=data["sector_code"],
                defaults={"is_other": False},
            )

            stage, _ = Stage.objects.get_or_create(
                code=data["stage_code"],
            )

            business_model, _ = BusinessModel.objects.get_or_create(
                code=data["bm_code"],
                defaults={"is_other": False} if hasattr(BusinessModel, "is_other") else {},
            )

            # У моделі Country поле name є:
            country, _ = Country.objects.get_or_create(
                code=data["country_code"],
                defaults={"name": data["country_name"]},
            )

            # 2. Користувач
            user, _ = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "role": UserRole.STARTUP,
                    "is_active": True,
                    "email_verified_at": now,
                    "is_test": True,
                },
            )
            if not user.has_usable_password():
                user.set_password("testpass123")
                user.save(update_fields=["password"])

            # 3. Профіль стартапу (із задоволенням усіх CheckConstraints)
            profile, _ = StartupProfile.objects.update_or_create(
                user=user,
                defaults={
                    "status": "LIVE",
                    "sector": sector,
                    "stage": stage,
                    "business_model": business_model,
                    "country": country,
                    "round_amount_eur": data["round_amount_eur"],
                    "mrr_eur": data["mrr_eur"],
                    "growth_pct": Decimal("15.00"),
                    "team_size": data["team_size"],
                    "went_live_at": now,  # <-- КРИТИЧНО ДЛЯ chk_startup_profiles_live_complete!
                },
            )

            # 4. Дек
            pitch_deck, _ = PitchDeck.objects.get_or_create(
                startup_profile=profile,
                defaults={
                    "file": f"decks/test_{data['country_code']}.pdf",
                    "original_name": f"{data['company_name'].lower().replace(' ', '_')}_deck.pdf",
                    "file_size_bytes": 150000,
                    "uploaded_at": now,
                },
            )

            # 5. Згода на Декларацію A (для chk_teasers_approval)
            consent = UserConsent.objects.create(
                user=user,
                legal_document=doc_a,
                context=UserConsentContext.TEASER_APPROVAL,
                accepted_at=now,
            )

            # 6. Затверджений тизер
            teaser, _ = Teaser.objects.update_or_create(
                startup_profile=profile,
                version=1,
                defaults={
                    "pitch_deck": pitch_deck,
                    "status": Teaser.Status.APPROVED,
                    "is_current": True,
                    "approved_at": now,
                    "declaration_consent": consent,
                },
            )

            # 7. Поля тизера
            for f_name, text in data["teaser"].items():
                TeaserField.objects.update_or_create(
                    teaser=teaser,
                    field_name=f_name,
                    language=Language.DE,
                    defaults={
                        "ai_text": text,
                        "final_text": text,
                        "approved_at": now,
                        "risk_phrases": [],
                    },
                )

            created_count += 1
            self.stdout.write(f"  ✓ Створено LIVE-стартап: {data['company_name']} ({data['sector_code']} / {data['stage_code']})")

        self.stdout.write(
            self.style.SUCCESS(f"\nУспішно підготовлено {created_count} стартапів для матчингу!")
        )

        if options["digest"]:
            try:
                from apps.investors.tasks import generate_weekly_digests
                result = generate_weekly_digests()
                self.stdout.write(self.style.SUCCESS(f"Генерація дайджестів: {result}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Не вдалося згенерувати дайджест: {e}"))
                
#   python manage.py seed_test_teasers
#   python manage.py seed_test_teasers --digest