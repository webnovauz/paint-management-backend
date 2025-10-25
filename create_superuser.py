#!/usr/bin/env python
"""Script to create superuser if not exists"""
import os
import django

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paint_management.settings')
    django.setup()

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print('✅ Superuser created: admin/admin123')
    else:
        print('ℹ️ Superuser already exists')
except Exception as e:
    print(f'⚠️ Error with superuser creation: {e}')
    # Continue anyway - this shouldn't stop the deployment