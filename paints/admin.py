from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PaintCategory, Paint, StockMovement, Sale, SaleItem,
    Supplier, Purchase, PurchaseItem, PriceHistory
)


@admin.register(PaintCategory)
class PaintCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Paint)
class PaintAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'color', 'brand', 'category', 'unit', 
        'cost_price', 'selling_price', 'current_stock_display', 'stock_status'
    ]
    list_filter = ['category', 'brand', 'unit', 'is_active']
    search_fields = ['name', 'color', 'brand', 'sku']
    readonly_fields = ['current_stock_display', 'created_at', 'updated_at']
    fieldsets = [
        ('Основная информация', {
            'fields': ('name', 'color', 'brand', 'category', 'sku')
        }),
        ('Цены и единицы', {
            'fields': ('unit', 'cost_price', 'selling_price', 'density')
        }),
        ('Остатки', {
            'fields': ('min_stock_level', 'current_stock_display')
        }),
        ('Дополнительно', {
            'fields': ('description', 'is_active', 'created_at', 'updated_at')
        })
    ]
    inlines = [StockMovementInline]

    def current_stock_display(self, obj):
        stock = obj.current_stock
        return f"{stock} {obj.unit}"
    current_stock_display.short_description = "Текущий остаток"

    def stock_status(self, obj):
        if obj.is_low_stock:
            return format_html(
                '<span style="color: red; font-weight: bold;">Низкий остаток</span>'
            )
        return format_html(
            '<span style="color: green;">Нормальный</span>'
        )
    stock_status.short_description = "Статус остатка"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'paint', 'movement_type', 'quantity', 'price_per_unit', 
        'total_cost', 'created_at'
    ]
    list_filter = ['movement_type', 'created_at', 'paint__category']
    search_fields = ['paint__name', 'notes']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ['total_price']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_number', 'customer_name', 'total_amount', 'created_at'
    ]
    search_fields = ['sale_number', 'customer_name', 'customer_phone']
    readonly_fields = ['sale_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [SaleItemInline]
    ordering = ['-created_at']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'contact_person', 'phone', 'email']


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ['total_cost']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'purchase_number', 'supplier', 'total_amount', 'created_at'
    ]
    list_filter = ['supplier', 'created_at']
    search_fields = ['purchase_number', 'supplier__name']
    readonly_fields = ['purchase_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [PurchaseItemInline]
    ordering = ['-created_at']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'paint', 'old_cost_price', 'new_cost_price', 
        'old_selling_price', 'new_selling_price', 'changed_by', 'created_at'
    ]
    list_filter = ['created_at', 'paint__category']
    search_fields = ['paint__name', 'changed_by', 'reason']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
