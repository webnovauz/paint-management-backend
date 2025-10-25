from django.shortcuts import render
from django.http import JsonResponse


def api_root(request):
    """Корневая страница API с документацией доступных endpoints"""
    if request.content_type == 'application/json' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({
            "message": "Paint Management System API",
            "version": "1.0",
            "endpoints": {
                "categories": "/api/categories/",
                "paints": "/api/paints/",
                "stock_movements": "/api/stock-movements/",
                "sales": "/api/sales/",
                "suppliers": "/api/suppliers/",
                "purchases": "/api/purchases/",
                "dashboard": "/api/dashboard/stats/",
                "admin": "/admin/"
            },
            "special_endpoints": {
                "low_stock_paints": "/api/paints/low_stock/",
                "adjust_stock": "/api/paints/{id}/adjust_stock/",
                "today_sales": "/api/sales/today/",
                "sales_stats": "/api/sales/stats/",
                "purchase_stats": "/api/purchases/stats/"
            }
        })
    
    # HTML-ответ для браузера
    context = {
        'title': 'Paint Management System',
        'endpoints': [
            {'name': 'Categories', 'url': '/api/categories/', 'description': 'Категории красок'},
            {'name': 'Paints', 'url': '/api/paints/', 'description': 'Управление красками'},
            {'name': 'Stock Movements', 'url': '/api/stock-movements/', 'description': 'Движения товаров'},
            {'name': 'Sales', 'url': '/api/sales/', 'description': 'Продажи'},
            {'name': 'Suppliers', 'url': '/api/suppliers/', 'description': 'Поставщики'},
            {'name': 'Purchases', 'url': '/api/purchases/', 'description': 'Закупки'},
            {'name': 'Dashboard', 'url': '/api/dashboard/stats/', 'description': 'Статистика'},
            {'name': 'Admin Panel', 'url': '/admin/', 'description': 'Административная панель'},
        ]
    }
    return render(request, 'paints/api_root.html', context)