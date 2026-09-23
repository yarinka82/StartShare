

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random

from apps.members.models import Member

# Данные для генерации
FIRST_NAMES = [
    'Олександр', 'Іван', 'Марія', 'Анна', 'Петро',
    'Олена', 'Василь', 'Наталія', 'Микола', 'Тетяна',
    'Юрій', 'Ольга', 'Володимир', 'Катерина', 'Андрій',
    'Ірина', 'Сергій', 'Людмила', 'Дмитро', 'Вікторія',
    'Євген', 'Ганна', 'Богдан', 'Зоя', 'Олег'
]

LAST_NAMES = [
    'Коваленко', 'Бондаренко', 'Ткаченко', 'Кравченко', 'Олійник',
    'Шевченко', 'Бойко', 'Мельник', 'Коваль', 'Савенко',
    'Гончаренко', 'Лисенко', 'Руденко', 'Ткачук', 'Марченко',
    'Кузьменко', 'Сидоренко', 'Клименко', 'Федоренко', 'Романенко',
    'Кравець', 'Денисенко', 'Білоус', 'Швець', 'Захарченко'
]

EMAIL_DOMAINS = ['gmail.com', 'ukr.net', 'email.ua', 'i.ua', 'meta.ua']

PHONE_PREFIXES = ['050', '063', '066', '067', '068', '093', '095', '096', '097', '098', '099']


class Command(BaseCommand):
    help = 'Заповнює базу даних тестовими членами'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Кількість членів для створення (за замовчуванням: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистити існуючих членів перед створенням'
        )
        parser.add_argument(
            '--founders',
            type=int,
            default=None,
            help='Кількість засновників (за замовчуванням: 2-3 випадково)'
        )
    
    def generate_phone(self):
        """Генерирует случайный украинский номер телефона"""
        prefix = random.choice(PHONE_PREFIXES)
        number = ''.join(str(random.randint(0, 9)) for _ in range(7))
        return f"{prefix}{number}"
    
    def generate_email(self, first_name, last_name):
        """Генерирует email на основе имени и фамилии"""
        domain = random.choice(EMAIL_DOMAINS)
        
        # Транслитерация для email
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g',
            'д': 'd', 'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z',
            'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k',
            'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
            'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
            'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ь': '', 'ю': 'yu', 'я': 'ya'
        }
        
        def transliterate(text):
            result = ''
            for char in text.lower():
                if char in translit_map:
                    result += translit_map[char]
                else:
                    result += char
            return result
        
        first = transliterate(first_name)
        last = transliterate(last_name)
        
        variants = [
            f"{first}.{last}",
            f"{first}{last}",
            f"{first}_{last}",
            f"{last}.{first}",
            f"{last}{random.randint(1, 99)}"
        ]
        
        return f"{random.choice(variants)}@{domain}"
    
    def handle(self, *args, **options):
        count = options['count']
        should_clear = options['clear']
        founder_count = options['founders']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('📝 ЗАПОВНЕННЯ БАЗИ ДАНИХ ЧЛЕНАМИ'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Очистка если нужно
        if should_clear:
            self.stdout.write('🗑️  Видаляємо існуючих членів...')
            deleted_count, _ = Member.objects.all().delete()
            self.stdout.write(f'   ✅ Видалено {deleted_count} членів')
        
        # Определяем количество засновників
        if founder_count is None:
            founder_count = random.randint(2, min(3, count))
        else:
            founder_count = min(founder_count, count)
        
        self.stdout.write(f'👥 Створюємо {count} членів ({founder_count} засновників)...')
        self.stdout.write('')
        
        created_count = 0
        for i in range(count):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            
            # Генерируем email
            email = self.generate_email(first_name, last_name)
            
            # Дата вступления (от 2020 до 2026)
            year = random.randint(2020, 2026)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            join_date = datetime(year, month, day).date()
            
            # Статус (80% активные, 20% неактивные)
            status = 'active' if random.random() < 0.8 else 'inactive'
            
            # Засновники (первые founder_count человек)
            is_founder = i < founder_count
            
            member = Member.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=self.generate_phone(),
                join_date=join_date,
                status=status,
                is_founder=is_founder,
            )
            created_count += 1
            
            # Показываем прогресс
            founder_mark = '⭐ Засновник' if is_founder else 'Член'
            self.stdout.write(
                f'  ✅ {member.last_name} {member.first_name} - {founder_mark}'
            )
        
        # Статистика
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ СТАТИСТИКА'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'   📊 Всього створено: {created_count}')
        self.stdout.write(f'   📊 Засновників: {Member.objects.filter(is_founder=True).count()}')
        self.stdout.write(f'   📊 Активних: {Member.objects.filter(status="active").count()}')
        self.stdout.write(f'   📊 Неактивних: {Member.objects.filter(status="inactive").count()}')
        
        # Показываем первых 5 членов
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('👥 Перші 5 членів:'))
        for member in Member.objects.all()[:5]:
            self.stdout.write(
                f'   - {member.last_name} {member.first_name} ({member.email})'
                f'{" ⭐" if member.is_founder else ""}'
            )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ Скрипт завершено!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
    #  Проверьте команду
    # python manage.py seed_members --help
    #
    # # Создайте 10 членов
    # python manage.py seed_members --count=10 --clear
        
        