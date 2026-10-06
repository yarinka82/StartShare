from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import LegalDocument, LegalDocumentCode, Language

DOCS_INITIAL = [
    # ------------------ AGB ------------------
    (
        LegalDocumentCode.AGB,
        Language.DE,
        "Allgemeine Geschäftsbedingungen",
        """AGB — Plattform für Matching zwischen Startups und Investoren (DE‑Recht)

1. Geltungsbereich
Diese Allgemeinen Geschäftsbedingungen (AGB) regeln die Nutzung der digitalen Plattform, über die Startups und Investoren miteinander in Kontakt gebracht werden („Plattform“).
Betreiber der Plattform ist Start Share, Sitz in Deutschland.

Die Plattform dient ausschließlich der Vermittlung von Kontakten und der Bereitstellung von Informationen.
Die Plattform ist kein Finanzdienstleister, kein Anlageberater und vermittelt keine Investments.

2. Nutzerrollen
Es gibt zwei Nutzergruppen:
- Startup: Unternehmen oder Gründer, die Kapital suchen.
- Investor: natürliche oder juristische Personen, die Investitionsmöglichkeiten prüfen.

Die Registrierung ist internationalen Nutzern gestattet.
Ein Anspruch auf Registrierung besteht nicht; der Betreiber kann Anmeldungen ablehnen.

3. Registrierung & Nutzerkonto
- Registrierung erfolgt mit wahrheitsgemäßen Angaben.
- Aktivierung erfolgt über Double‑Opt‑In.
- Nutzer dürfen nur ein Konto besitzen.
- Rollen (Startup/Investor) werden bei Registrierung festgelegt und können nicht selbstständig geändert werden.

4. Leistungsumfang der Plattform
Die Plattform bietet:
- Erstellung eines Nutzerprofils
- Upload von Pitch Decks (PDF)
- Matching‑Funktionen zwischen Startups und Investoren
- Bereitstellung von Informationen über Startups bzw. Investoren

Die Nutzung ist kostenfrei.
Der Betreiber schuldet nicht den Abschluss oder Erfolg einer Investition.
Verträge zwischen Startup und Investor kommen ausschließlich zwischen diesen Parteien zustande.

5. Inhalte der Nutzer
- Nutzer sind für alle hochgeladenen Inhalte selbst verantwortlich.
- Verboten sind rechtswidrige, irreführende oder schädliche Inhalte.
- Der Betreiber kann Inhalte prüfen und entfernen, wenn sie gegen diese AGB verstoßen.

6. Pitch Decks & Dateien
- Erlaubt sind ausschließlich PDF‑Dateien.
- Der Betreiber kann Dateien aus Sicherheitsgründen scannen oder ablehnen.
- Der Betreiber übernimmt keine Haftung für die Richtigkeit der Inhalte.

7. Verfügbarkeit der Plattform
- Der Betreiber bemüht sich um eine hohe Verfügbarkeit, garantiert diese jedoch nicht.
- Wartungen, Updates oder technische Probleme können zu Ausfällen führen.

8. Haftung
- Der Betreiber haftet nur für Vorsatz und grobe Fahrlässigkeit.
- Keine Haftung für Investitionsentscheidungen, Verluste oder Schäden, die aus der Nutzung der Plattform entstehen.
- Keine Haftung für Inhalte der Nutzer.

9. Änderungen der AGB
Der Betreiber kann diese AGB ändern.
Änderungen werden den Nutzern mitgeteilt.
Die weitere Nutzung der Plattform gilt als Zustimmung.

10. Kündigung & Löschung
- Nutzer können ihr Konto jederzeit löschen.
- Mit Löschung werden Pitch Decks und Profilinformationen entfernt, soweit keine gesetzlichen Aufbewahrungspflichten bestehen.
- Der Betreiber kann Konten sperren oder löschen, wenn gegen AGB verstoßen wird.

11. Datenschutz
Die Verarbeitung personenbezogener Daten erfolgt gemäß der Datenschutzerklärung der Plattform und der DSGVO.
Nutzer müssen der Datenschutzerklärung zustimmen.

12. Anwendbares Recht
Es gilt deutsches Recht.
Gerichtsstand ist der Sitz des Plattformbetreibers, sofern gesetzlich zulässig.
""",
        "2026-10-01",
    ),

    # ------------------ DSE ------------------
    (
        LegalDocumentCode.DSE,
        Language.DE,
        "Datenschutzerklärung",
        """Datenschutzerklärung

Diese Datenschutzerklärung informiert über die Verarbeitung personenbezogener Daten bei der Nutzung der digitalen Plattform, über die Startups und Investoren miteinander in Kontakt gebracht werden („Plattform“).
Verantwortlicher gemäß Art. 4 Nr. 7 DSGVO ist:
Start Share, Sitz in Deutschland.
""",
        "2026-10-01",
    ),

    # ------------------ A: Startup declaration ------------------
    (
        LegalDocumentCode.A,
        Language.DE,
        "Erklärung des Startups",
        "Ich bestätige, dass die Angaben nach bestem Wissen richtig sind und ich zur Weitergabe dieser Informationen berechtigt bin. Das hochgeladene Material enthält keine Rechte Dritter oder personenbezogenen Daten Dritter, die ich nicht weitergeben darf. Mir ist bekannt, dass Start Share die Angaben nicht prüft.",
        "2026-10-01",
    ),

    # ------------------ B: Teaser disclaimer ------------------
    (
        LegalDocumentCode.B,
        Language.DE,
        "Teaser Disclaimer",
        "Angaben des Startups, nicht von Start Share geprüft. Keine Anlageberatung, keine Empfehlung und kein Angebot zum Erwerb von Beteiligungen.",
        "2026-10-01",
    ),

    # ------------------ C: Investor confirmation ------------------
    (
        LegalDocumentCode.C,
        Language.DE,
        "Bestätigung Investor",
        "Ich handle als professioneller Investor bzw. Business Angel im Rahmen meiner unternehmerischen Tätigkeit und nicht als Verbraucher.",
        "2026-10-01",
    ),

    # ------------------ D: Startup contact request ------------------
    (
        LegalDocumentCode.D,
        Language.DE,
        "Kontaktanfrage Startup",
        "[Fonds] hat Interesse an Ihrem Profil. Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben.",
        "2026-10-01",
    ),

    # ------------------ E: Intro email signature ------------------
    (
        LegalDocumentCode.E,
        Language.DE,
        "E-Mail-Hinweis Intro",
        "Start Share vermittelt nur den Kontakt und ist nicht Partei von Gesprächen oder Verträgen. Bitte behandeln Sie ausgetauschte Informationen vertraulich.",
        "2026-10-01",
    ),

    # ------------------ F: Profile selection criteria ------------------
    (
        LegalDocumentCode.F,
        Language.DE,
        "Kriterien zur Profilauswahl",
        "Wir wählen Profile ausschließlich anhand der von Ihnen angegebenen Kriterien (Branche, Stadium, Region, Volumen). Es gibt keine bezahlten Platzierungen und keine Bewertung durch einen Score.",
        "2026-10-01",
    ),

    # ------------------ G: AI disclosure notice ------------------
    (
        LegalDocumentCode.G,
        Language.DE,
        "Hinweis zum Einsatz von KI",
        "Den Teaser-Entwurf erstellen wir mit Hilfe von KI aus Ihrem Deck. Sie prüfen und geben ihn frei. Ihr Deck wird nicht zum Training von KI-Modellen verwendet.",
        "2026-10-01",
    ),
]


class Command(BaseCommand):
    help = "Seeds initial legal documents (v1)"

    def handle(self, *args, **options):
        now = timezone.now()
        created_count = 0
        existing_count = 0

        for code, lang, title, body, _ in DOCS_INITIAL:
            doc, created = LegalDocument.objects.get_or_create(
                code=code,
                language=lang,
                version=1,
                defaults={
                    "title": title,
                    "body": body,
                    "legal_approved_at": now,
                    "valid_from": now,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {code} ({lang}) v1"))
            else:
                existing_count += 1
                self.stdout.write(f"Already exists: {code} ({lang}) v1")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished! Added {created_count} new documents, {existing_count} already existed."
            )
        )
        
        
##  python manage.py seed_legal_documents