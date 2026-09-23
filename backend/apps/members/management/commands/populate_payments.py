"""

Наполняет таблицу Payment тестовыми данными.

Использование:
    python manage.py populate_payments
    python manage.py populate_payments --count 200
    python manage.py populate_payments --count 50 --flush   # сначала очистить таблицу
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.payments.models import Payment
from apps.members.models import Member

SPONSOR_NAMES = [
    "Stadtwerke Kaiserslautern GmbH",
    "Sparkasse Rheinpfalz",
    "Volksbank Kaiserslautern eG",
    "Familie Müller-Stiftung",
    "Rotary Club Kaiserslautern",
    "Lions Club Pfalz",
    "Global Sports Foundation",
    "EU Erasmus+ Programme",
    "Land Rheinland-Pfalz — Sportförderung",
    "Bundesministerium für Familie",
]

GRANT_AGREEMENT_PREFIX = "GA-"


def random_date(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def random_period(d: date) -> str:
    # Иногда просто год, иногда квартал
    if random.random() < 0.5:
        return str(d.year)
    quarter = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{quarter}"


class Command(BaseCommand):
    help = "Наполняет таблицу Payment тестовыми данными"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=150,
            help="Сколько записей Payment создать (по умолчанию 150)",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Удалить все существующие Payment перед наполнением",
        )
        parser.add_argument(
            "--members-only",
            action="store_true",
            help="Создавать только membership_fee (для проверки биллинга по членам)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        flush = options["flush"]
        members_only = options["members_only"]

        if flush:
            deleted, _ = Payment.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Удалено записей: {deleted}"))

        members = list(Member.objects.all())
        if not members:
            self.stdout.write(
                self.style.ERROR(
                    "В базе нет ни одного Member — сначала создай хотя бы несколько членов "
                    "(membership_fee не может быть создан без member)."
                )
            )
            return

        start_date = date.today() - timedelta(days=3 * 365)
        end_date = date.today()

        types = (
            [Payment.PaymentType.MEMBERSHIP_FEE]
            if members_only
            else [
                Payment.PaymentType.MEMBERSHIP_FEE,
                Payment.PaymentType.DONATION,
                Payment.PaymentType.SPONSORSHIP,
                Payment.PaymentType.GRANT,
            ]
        )
        # membership_fee встречается чаще остальных — это же основной поток
        weights = [70, 15, 10, 5] if not members_only else [100]

        payments = []
        for i in range(count):
            ptype = random.choices(types, weights=weights, k=1)[0]
            d = random_date(start_date, end_date)
            status = random.choices(
                [Payment.PaymentStatus.PAID, Payment.PaymentStatus.OWED],
                weights=[80, 20],
                k=1,
            )[0]

            kwargs = dict(
                date=d,
                status=status,
                type=ptype,
            )

            if ptype == Payment.PaymentType.MEMBERSHIP_FEE:
                kwargs["member"] = random.choice(members)
                kwargs["amount"] = Decimal(random.choice([20, 30, 40, 50, 60]))
                kwargs["period"] = random_period(d)
                kwargs["source_name"] = ""
                kwargs["comment"] = ""
            elif ptype == Payment.PaymentType.DONATION:
                kwargs["member"] = None
                kwargs["amount"] = Decimal(random.randrange(10, 2000)).quantize(Decimal("1.00"))
                kwargs["source_name"] = random.choice(
                    ["Anonym", *random.sample(SPONSOR_NAMES, 3)]
                )
                kwargs["comment"] = ""
            elif ptype == Payment.PaymentType.SPONSORSHIP:
                kwargs["member"] = None
                kwargs["amount"] = Decimal(random.randrange(200, 15000)).quantize(Decimal("1.00"))
                kwargs["source_name"] = random.choice(SPONSOR_NAMES)
                kwargs["comment"] = random.choice(
                    ["", "Логотип на форме", "Спонсорство турнира", "Годовой пакет"]
                )
            elif ptype == Payment.PaymentType.GRANT:
                kwargs["member"] = None
                kwargs["amount"] = Decimal(random.randrange(1000, 50000)).quantize(Decimal("1.00"))
                kwargs["source_name"] = random.choice(SPONSOR_NAMES)
                kwargs["comment"] = f"{GRANT_AGREEMENT_PREFIX}{random.randint(1000, 9999)}"

            payments.append(Payment(**kwargs))

            # Пачками по 500, чтобы не держать все объекты в памяти разом на больших count
            if len(payments) >= 500:
                Payment.objects.bulk_create(payments)
                payments = []

        if payments:
            Payment.objects.bulk_create(payments)

        self.stdout.write(self.style.SUCCESS(f"Создано платежей: {count}"))