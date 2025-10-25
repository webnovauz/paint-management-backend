#!/bin/bash

echo "🚀 Starting Django deployment process..."

echo "📊 Running database migrations..."
python manage.py migrate

echo "👤 Creating superuser if not exists..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
EOF

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "🎉 Deployment complete! Starting server..."
python manage.py runserver 0.0.0.0:$PORT