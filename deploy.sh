#!/bin/bash

echo "🚀 Starting Django deployment process..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL not set, using SQLite fallback"
else
    echo "✅ DATABASE_URL configured for production database"
fi

echo "📊 Running database migrations..."
python manage.py migrate --noinput

if [ $? -ne 0 ]; then
    echo "❌ Migration failed!"
    exit 1
fi

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

if [ $? -ne 0 ]; then
    echo "❌ Static files collection failed!"
    exit 1
fi

echo "🔍 Running Django check..."
python manage.py check --deploy

if [ $? -ne 0 ]; then
    echo "⚠️ Django check found issues, but continuing..."
fi

echo "🎉 Deployment complete! Starting server..."

# Use PORT environment variable or default to 8000
PORT=${PORT:-8000}
echo "🌐 Starting server on port $PORT"

python manage.py runserver 0.0.0.0:$PORT