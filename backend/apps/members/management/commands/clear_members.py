
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.members.models import Member


def clear_members():
    count = Member.objects.count()
    if count == 0:
        print("ℹ️ База данных уже пуста")
        return
    
    confirm = input(f"⚠️ Вы уверены, что хотите удалить всех {count} членов? (y/N): ")
    if confirm.lower() == 'y':
        Member.objects.all().delete()
        print(f"✅ Удалено {count} членов")
    else:
        print("❌ Операция отменена")


if __name__ == "__main__":
    clear_members()