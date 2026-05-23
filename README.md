# Flower Choco Shop

نظام إدارة محل ورد وشوكولاته مبني باستخدام Django.

## التشغيل المحلي

1. إنشاء البيئة الافتراضية وتفعيلها
2. تثبيت الحزم: pip install -r requirements.txt
3. إنشاء ملف البيئة: انسخ .env.example إلى .env
4. تنفيذ الترحيلات: python manage.py migrate
5. إعداد الصلاحيات والفئات:
   - python manage.py setup_permissions
   - python manage.py seed_expense_categories
6. تشغيل الخادم: python manage.py runserver

## النشر على Render

1. ارفع المشروع إلى GitHub.
2. أنشئ Blueprint جديد في Render من نفس المستودع.
3. استخدم الملف render.yaml.
4. تأكد من تعيين DJANGO_SETTINGS_MODULE=shop_management.settings_production.
5. بعد أول نشر، نفذ create superuser من Render Shell:
   - python manage.py createsuperuser

## Docker

- تشغيل الخدمات: docker compose up --build
- إيقاف الخدمات: docker compose down

## المتغيرات المهمة

راجع ملف .env.example لجميع المتغيرات المطلوبة.
