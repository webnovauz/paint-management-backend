from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import (
    PaintCategory, Paint, StockMovement, Sale, SaleItem,
    Supplier, Purchase, PurchaseItem, PriceHistory, Customer, Payment
)


class PaintCategorySerializer(serializers.ModelSerializer):
    paints_count = serializers.SerializerMethodField()

    class Meta:
        model = PaintCategory
        fields = ['id', 'name', 'description', 'paints_count', 'created_at']

    def get_paints_count(self, obj):
        return obj.paints.filter(is_active=True).count()


class PaintSerializer(serializers.ModelSerializer):
    current_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    profit_margin = serializers.ReadOnlyField()
    profit_per_unit = serializers.ReadOnlyField()

    class Meta:
        model = Paint
        fields = [
            'id', 'name', 'category', 'category_name', 'color', 'brand',
            'unit', 'product_type', 'cost_price', 'selling_price', 'profit_margin', 'profit_per_unit',
            'density', 'description', 'sku', 'min_stock_level', 
            'current_stock', 'is_low_stock', 'is_active', 'created_at', 'updated_at'
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    paint_name = serializers.CharField(source='paint.name', read_only=True)
    paint_color = serializers.CharField(source='paint.color', read_only=True)
    paint_unit = serializers.CharField(source='paint.unit', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'paint', 'paint_name', 'paint_color', 'paint_unit',
            'movement_type', 'quantity', 'price_per_unit', 'total_cost',
            'notes', 'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by']

    def create(self, validated_data):
        # Автоматически заполняем created_by
        validated_data['created_by'] = 'Manual adjustment'
        return super().create(validated_data)


class SaleItemSerializer(serializers.ModelSerializer):
    paint_name = serializers.CharField(source='paint.name', read_only=True)
    paint_color = serializers.CharField(source='paint.color', read_only=True)
    paint_unit = serializers.CharField(source='paint.unit', read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            'id', 'paint', 'paint_name', 'paint_color', 'paint_unit',
            'quantity', 'unit_price', 'total_price', 'created_at'
        ]
        read_only_fields = ['total_price']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    customer_name_display = serializers.CharField(source='customer.name', read_only=True)
    debt_amount = serializers.ReadOnlyField()
    payment_status = serializers.ReadOnlyField()
    is_fully_paid = serializers.ReadOnlyField()

    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name', 'customer_name_display', 
            'customer_phone', 'total_amount', 'paid_amount', 'debt_amount',
            'payment_type', 'payment_status', 'is_fully_paid', 'notes',
            'items', 'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['sale_number', 'total_amount', 'customer_name', 'customer_phone']

    def get_items_count(self, obj):
        return obj.items.count()


class SupplierSerializer(serializers.ModelSerializer):
    purchases_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'phone', 'email',
            'address', 'purchases_count', 'is_active', 'created_at'
        ]

    def get_purchases_count(self, obj):
        return obj.purchase_set.count()


class PurchaseItemSerializer(serializers.ModelSerializer):
    paint_name = serializers.CharField(source='paint.name', read_only=True)
    paint_color = serializers.CharField(source='paint.color', read_only=True)
    paint_unit = serializers.CharField(source='paint.unit', read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'paint', 'paint_name', 'paint_color', 'paint_unit',
            'quantity', 'unit_cost', 'total_cost', 'created_at'
        ]
        read_only_fields = ['total_cost']


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            'id', 'purchase_number', 'supplier', 'supplier_name',
            'total_amount', 'notes', 'items', 'items_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['purchase_number', 'total_amount']

    def get_items_count(self, obj):
        return obj.items.count()


# Специальные сериализаторы для создания продаж и закупок с позициями
class CreateSaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ['paint', 'quantity', 'unit_price']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше нуля")
        return value

    def validate(self, data):
        print(f"CreateSaleItemSerializer validate data: {data}")
        paint = data['paint']
        quantity = data['quantity']
        
        # Проверяем тип товара и валидируем количество
        if paint.product_type == 'piece':
            # Для штучных товаров количество должно быть целым числом
            if quantity != int(quantity):
                error_msg = f"Для штучного товара '{paint.name}' количество должно быть целым числом"
                print(f"Validation error: {error_msg}")
                raise serializers.ValidationError(error_msg)
        
        # Проверяем доступность товара на складе
        if paint.current_stock < quantity:
            error_msg = f"Недостаточно товара на складе. Доступно: {paint.current_stock} {paint.unit}"
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError(error_msg)
        
        return data


class CreateSaleSerializer(serializers.ModelSerializer):
    items = CreateSaleItemSerializer(many=True)
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        required=False,
        allow_null=True,
        allow_empty=True
    )
    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Sale
        fields = ['customer', 'customer_name', 'customer_phone', 'paid_amount', 'payment_type', 'notes', 'items']

    def validate(self, data):
        print(f"CreateSaleSerializer validate data: {data}")
        
        # Если customer передан как пустая строка или None, устанавливаем None
        if 'customer' in data and (data['customer'] == '' or data['customer'] == 'null'):
            data['customer'] = None
        
        # Если paid_amount не передан, пустой или None, устанавливаем 0
        if 'paid_amount' not in data or data['paid_amount'] is None or data['paid_amount'] == '':
            data['paid_amount'] = Decimal('0')
        elif isinstance(data['paid_amount'], str):
            try:
                data['paid_amount'] = Decimal(data['paid_amount'])
            except:
                data['paid_amount'] = Decimal('0')
        
        # Автоматически создаем клиента, если он не выбран, но указаны имя и телефон
        if not data.get('customer') and data.get('customer_name') and data.get('customer_phone'):
            customer_name = data['customer_name'].strip()
            customer_phone = data['customer_phone'].strip()
            
            if customer_name and customer_phone:
                # Проверяем, есть ли уже клиент с таким телефоном
                existing_customer = Customer.objects.filter(phone=customer_phone).first()
                
                if existing_customer:
                    # Если клиент с таким телефоном уже существует, используем его
                    data['customer'] = existing_customer
                    print(f"Найден существующий клиент: {existing_customer.name}")
                else:
                    # Создаем нового клиента
                    new_customer = Customer.objects.create(
                        name=customer_name,
                        phone=customer_phone,
                        email='',  # пустой email
                        address=''  # пустой адрес
                    )
                    data['customer'] = new_customer
                    print(f"Создан новый клиент: {new_customer.name} ({new_customer.phone})")
            
        return data

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = Sale.objects.create(**validated_data)
        
        # Создаем позиции продажи и рассчитываем общую сумму
        total_amount = Decimal('0')
        for item_data in items_data:
            # StockMovement создается автоматически в методе save() модели SaleItem
            sale_item = SaleItem.objects.create(sale=sale, **item_data)
            total_amount += sale_item.total_price
        
        # Обновляем общую сумму продажи
        sale.total_amount = total_amount
        sale.save()
        
        # Обновляем баланс клиента, если есть долг
        if sale.customer:
            debt_amount = sale.total_amount - sale.paid_amount
            if debt_amount > 0:
                sale.customer.balance += debt_amount
                sale.customer.save()
        
        return sale


class CreatePurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ['paint', 'quantity', 'unit_cost']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше нуля")
        return value


class CreatePurchaseSerializer(serializers.ModelSerializer):
    items = CreatePurchaseItemSerializer(many=True)

    class Meta:
        model = Purchase
        fields = ['supplier', 'notes', 'items']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        purchase = Purchase.objects.create(**validated_data)
        
        for item_data in items_data:
            # StockMovement создается автоматически в методе save() модели PurchaseItem
            PurchaseItem.objects.create(purchase=purchase, **item_data)
        
        return purchase


class PriceHistorySerializer(serializers.ModelSerializer):
    paint_name = serializers.CharField(source='paint.name', read_only=True)
    cost_price_change_percent = serializers.ReadOnlyField()
    selling_price_change_percent = serializers.ReadOnlyField()

    class Meta:
        model = PriceHistory
        fields = [
            'id', 'paint', 'paint_name', 'old_cost_price', 'new_cost_price',
            'old_selling_price', 'new_selling_price', 'cost_price_change_percent',
            'selling_price_change_percent', 'changed_by', 'reason', 'created_at'
        ]
        read_only_fields = ['created_at']


# Сериализатор для статистики
class DashboardStatsSerializer(serializers.Serializer):
    total_paints = serializers.IntegerField()
    low_stock_paints = serializers.IntegerField()
    today_sales_count = serializers.IntegerField()
    today_sales_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_stock_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Дополнительные поля для периодной статистики
    period_sales_count = serializers.IntegerField(required=False)
    period_sales_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    period_profit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    start_date = serializers.CharField(required=False)
    end_date = serializers.CharField(required=False)


class CustomerSerializer(serializers.ModelSerializer):
    debt_amount = serializers.ReadOnlyField()
    prepayment_amount = serializers.ReadOnlyField()
    has_debt = serializers.ReadOnlyField()
    has_prepayment = serializers.ReadOnlyField()
    sales_count = serializers.SerializerMethodField()
    total_purchases = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'balance',
            'debt_amount', 'prepayment_amount', 'has_debt', 'has_prepayment',
            'sales_count', 'total_purchases', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_sales_count(self, obj):
        """Количество продаж клиента"""
        return obj.sales.count()

    def get_total_purchases(self, obj):
        """Общая сумма покупок клиента"""
        return obj.sales.aggregate(
            total=serializers.models.Sum('total_amount')
        )['total'] or 0


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'customer', 'customer_name', 'amount', 'payment_type',
            'payment_date', 'notes', 'created_by', 'created_at'
        ]
        read_only_fields = ['payment_date', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма платежа должна быть больше нуля")
        return value


class CreatePaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для создания платежа с автоматическим обновлением баланса"""
    
    class Meta:
        model = Payment
        fields = ['customer', 'amount', 'payment_type', 'notes', 'created_by']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма платежа должна быть больше нуля")
        return value

    def create(self, validated_data):
        # Баланс клиента обновляется автоматически в методе save() модели Payment
        return super().create(validated_data)


class CustomerBalanceSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра детального баланса клиента"""
    recent_sales = serializers.SerializerMethodField()
    recent_payments = serializers.SerializerMethodField()
    debt_amount = serializers.ReadOnlyField()
    prepayment_amount = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'balance', 'debt_amount', 'prepayment_amount',
            'recent_sales', 'recent_payments'
        ]

    def get_recent_sales(self, obj):
        """Последние 5 продаж клиента"""
        recent_sales = obj.sales.order_by('-created_at')[:5]
        return [
            {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'total_amount': sale.total_amount,
                'paid_amount': sale.paid_amount,
                'debt_amount': sale.debt_amount,
                'payment_status': sale.payment_status,
                'created_at': sale.created_at
            }
            for sale in recent_sales
        ]

    def get_recent_payments(self, obj):
        """Последние 5 платежей клиента"""
        recent_payments = obj.payments.order_by('-payment_date')[:5]
        return PaymentSerializer(recent_payments, many=True).data