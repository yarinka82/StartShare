import os
from django.core.wsgi import get_wsgi_application

# Если settings.py в корне backend
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# Или если в папке backend
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()