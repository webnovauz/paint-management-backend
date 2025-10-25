from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_main import api_root

router = DefaultRouter()
router.register(r'categories', views.PaintCategoryViewSet)
router.register(r'paints', views.PaintViewSet)
router.register(r'stock-movements', views.StockMovementViewSet)
router.register(r'sales', views.SaleViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'purchases', views.PurchaseViewSet)
router.register(r'customers', views.CustomerViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('welcome/', api_root, name='api_root'),  # Переместили на /welcome/
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),  # Добавили DRF auth URLs
    path('', include(router.urls)),  # Теперь корень показывает DRF API
]