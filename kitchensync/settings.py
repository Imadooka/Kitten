from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-phisfaay#_q7%2wjyi56md5fd^xytq1xd6$p#ca8aqjve-w6ac'
DEBUG = True  # โปรดเปลี่ยนเป็น False ตอนโปรดักชัน

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]  # ใส่ Public IP/โดเมนของ VM2 ที่นี่ตอนดีพลอย

SPOONACULAR_API_KEY = '4e8cc3a8b81e4022828e53a7ad94bc9d' # ใส่ API Key ของ Spoonacular ที่นี่ 
SPOONACULAR_API_KEY = os.environ.get("S4e8cc3a8b81e4022828e53a7ad94bc9d", "")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'index',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kitchensync.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # ใช้ templates ใน app
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "django.template.context_processors.media",
            ],
        },
    },
]

WSGI_APPLICATION = 'kitchensync.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'kitchensync_db',
        'USER': 'root',
        'PASSWORD': '12345678',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True

# Static / Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'     # สำหรับ collectstatic ตอนโปรดักชัน
# STATICFILES_DIRS = [BASE_DIR / 'static'] # (ถ้ามีโฟลเดอร์ static ฝั่งโปรเจกต์)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
