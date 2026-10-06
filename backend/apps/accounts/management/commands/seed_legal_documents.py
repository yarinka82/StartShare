
# backend/apps/accounts/management/commands/seed_legal_documents.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import LegalDocument, LegalDocumentCode, Language

DOCS_INITIAL = [
    (
        LegalDocumentCode.AGB,
        Language.DE,
        "Allgemeine Geschäftsbedingungen",
        """AGB — Plattform für Matching zwischen Startups und Investoren (DE‑Recht)

1. Geltungsbereich
Diese Allgemeinen Geschäftsbedingungen (AGB) regeln die Nutzung der digitalen Plattform, über die Startups und Investoren miteinander in Kontakt gebracht werden („Plattform“).
Betreiber der Plattform ist [Name deiner Firma], Sitz in Deutschland.

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
        "2026-10-01"
    ),
    
    (
        LegalDocumentCode.DSE,
        Language.DE,
        "Datenschutzerklärung",
        """Datenschutzerklärung

    Diese Datenschutzerklärung informiert über die Verarbeitung personenbezogener Daten bei der Nutzung der digitalen Plattform, über die Startups und Investoren miteinander in Kontakt gebracht werden („Plattform“).
    Verantwortlicher gemäß Art. 4 Nr. 7 DSGVO ist:
    [Name deiner Firma], Sitz in Deutschland.
    """,
        "2026-10-01"
    ),
    
    (
        LegalDocumentCode.A,
        Language.DE,
        "Erklärung des Startups",
        "Ich bestätige, dass die Angaben nach bestem Wissen richtig sind und ich zur Weitergabe dieser Informationen berechtigt bin. Das hochgeladene Material enthält keine Rechte Dritter oder personenbezogenen Daten Dritter, die ich nicht weitergeben darf. Mir ist bekannt, dass Start Share die Angaben nicht prüft.",
        "2026-10-01"
    ),
    
    (
        LegalDocumentCode.C,
        Language.DE,
        "Bestätigung Investor",
        "Ich handle als professioneller Investor bzw. Business Angel im Rahmen meiner unternehmerischen Tätigkeit und nicht als Verbraucher.",
        "2026-10-01"
    ),
]

class Command(BaseCommand):
    help = "Seeds initial legal documents (v1)"

    def handle(self, *args, **options):
        now = timezone.now()
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
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {code} ({lang}) v1"))
        self.stdout.write(self.style.SUCCESS("Legal documents seeded successfully!"))