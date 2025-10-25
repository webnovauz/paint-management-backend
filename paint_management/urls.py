"""
URL configuration for paint_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    """Simple health check endpoint for Railway - no DB required"""
    return JsonResponse({
        'status': 'healthy', 
        'service': 'paint-management-backend',
        'timestamp': str(request.META.get('HTTP_DATE', 'unknown'))
    })

def db_check(request):
    """Database health check endpoint"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({
            'status': 'healthy', 
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'database': 'disconnected', 
            'error': str(e)
        }, status=500)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),  # Simple health check
    path('health/db/', db_check, name='db_check'),  # Database health check
    path('', include('paints.urls')),
]

# Добавляем обслуживание медиа файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
