
import os

from django.core.asgi import get_asgi_application

# Устанавливаем модуль настроек
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Создаем ASGI приложение
application = get_asgi_application()