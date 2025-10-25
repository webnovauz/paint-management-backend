from django.shortcuts import render
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, BooleanFilter
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

from .models import (
    PaintCategory, Paint, StockMovement, Sale, SaleItem,
    Supplier, Purchase, PurchaseItem, Customer, Payment
)
from .serializers import (
    PaintCategorySerializer, PaintSerializer, StockMovementSerializer,
    SaleSerializer, CreateSaleSerializer, SupplierSerializer,
    PurchaseSerializer, CreatePurchaseSerializer,
    DashboardStatsSerializer, CustomerSerializer, PaymentSerializer,
    CreatePaymentSerializer, CustomerBalanceSerializer
)


class CustomerFilter(FilterSet):
    """Кастомный фильтр для клиентов"""
    has_debt = BooleanFilter(method='filter_has_debt')
    
    class Meta:
        model = Customer
        fields = ['is_active']
    
    def filter_has_debt(self, queryset, name, value):
        """Фильтрация по наличию долга"""
        if value is True:
            return queryset.filter(balance__gt=0)
        elif value is False:
            return queryset.filter(balance__lte=0)
        return queryset


class PaintCategoryViewSet(viewsets.ModelViewSet):
    queryset = PaintCategory.objects.all()
    serializer_class = PaintCategorySerializer
    ordering = ['name']


class PaintViewSet(viewsets.ModelViewSet):
    queryset = Paint.objects.all()
    serializer_class = PaintSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'unit', 'is_active']
    search_fields = ['name', 'color', 'brand', 'sku']
    ordering_fields = ['name', 'color', 'cost_price', 'selling_price', 'current_stock']
    ordering = ['name', 'color']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Получить краски с низким остатком"""
        low_stock_paints = []
        for paint in self.get_queryset().filter(is_active=True):
            if paint.is_low_stock:
                low_stock_paints.append(paint)
        
        # Отключаем пагинацию для этого endpoint
        serializer = self.get_serializer(low_stock_paints, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Корректировка остатков"""
        paint = self.get_object()
        quantity = request.data.get('quantity')
        notes = request.data.get('notes', '')
        
        if quantity is None:
            return Response(
                {'error': 'Количество обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = Decimal(str(quantity))
        except:
            return Response(
                {'error': 'Некорректное количество'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем корректировку
        StockMovement.objects.create(
            paint=paint,
            movement_type='adjustment',
            quantity=quantity,
            notes=notes or 'Ручная корректировка остатков'
        )
        
        return Response({'message': 'Остатки скорректированы'})


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related('paint').all()
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paint', 'movement_type']
    ordering = ['-created_at']
    search_fields = ['paint__name', 'notes']  # Поиск по названию краски и заметкам
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            
        return queryset


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    ordering = ['-created_at']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'items__paint']
    search_fields = ['sale_number', 'customer__name', 'notes']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSaleSerializer
        return SaleSerializer

    def create(self, request, *args, **kwargs):
        """Создание продажи с логированием"""
        logger.info(f"Sale creation request data: {request.data}")
        print(f"Sale creation request data: {request.data}")
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"Sale creation successful: {response.data}")
            print(f"Sale creation successful: {response.data}")
            return response
        except Exception as e:
            logger.error(f"Sale creation error: {e}")
            logger.error(f"Error type: {type(e)}")
            print(f"Sale creation error: {e}")
            print(f"Error type: {type(e)}")
            raise

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Продажи за сегодня"""
        # Получаем текущую дату в локальном часовом поясе
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # Продажи за сегодня
        # Для SQLite используем простое сравнение дат
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        today_sales = self.get_queryset().filter(created_at__range=[today_start, today_end])
        # Отключаем пагинацию для сегодняшних продаж
        serializer = self.get_serializer(today_sales, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика продаж"""
        # Получаем текущую дату в локальном часовом поясе
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # Продажи за сегодня
        # Для SQLite используем простое сравнение дат
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        today_sales = self.get_queryset().filter(created_at__range=[today_start, today_end])
        
        stats = {
            'today_count': today_sales.count(),
            'today_amount': today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
            'total_count': self.get_queryset().count(),
            'total_amount': self.get_queryset().aggregate(
                Sum('total_amount')
            )['total_amount__sum'] or Decimal('0')
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def product_stats(self, request):
        """Статистика продаж по товарам"""
        from datetime import datetime
        
        # Получаем параметры фильтрации
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        # Фильтруем по периоду, если указан
        queryset = Sale.objects.all()
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                
                period_start = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
                period_end = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
                
                queryset = queryset.filter(created_at__range=[period_start, period_end])
            except ValueError:
                return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}, status=400)
        
        # Статистика по товарам через SaleItem
        product_stats = []
        
        # Получаем все товары, которые были проданы в указанный период
        paint_items = SaleItem.objects.filter(sale__in=queryset).values('paint').distinct()
        
        for item in paint_items:
            paint_id = item['paint']
            paint = Paint.objects.get(id=paint_id)
            
            # Агрегируем данные по этому товару
            paint_sales = SaleItem.objects.filter(
                sale__in=queryset,
                paint_id=paint_id
            ).aggregate(
                total_quantity=Sum('quantity'),
                total_amount=Sum(F('quantity') * F('unit_price')),
                sales_count=Count('sale', distinct=True)
            )
            
            # Рассчитываем среднюю цену
            avg_price = float(paint_sales['total_amount'] or 0) / float(paint_sales['total_quantity'] or 1)
            
            product_stats.append({
                'product_id': paint.id,
                'product_name': paint.name,
                'product_color': paint.color,
                'product_unit': paint.unit,
                'total_quantity': str(paint_sales['total_quantity'] or 0),
                'total_amount': str(paint_sales['total_amount'] or 0),
                'average_price': str(avg_price),
                'sales_count': paint_sales['sales_count'] or 0,
                'percentage_of_total_sales': 0  # Рассчитаем позже
            })
        
        # Рассчитываем проценты
        total_sales_amount = sum(float(stat['total_amount']) for stat in product_stats)
        for stat in product_stats:
            if total_sales_amount > 0:
                stat['percentage_of_total_sales'] = (float(stat['total_amount']) / total_sales_amount) * 100
        
        # Сортируем по убыванию суммы
        product_stats.sort(key=lambda x: float(x['total_amount']), reverse=True)
        
        return Response(product_stats)

    @action(detail=False, methods=['get'])
    def customer_stats(self, request):
        """Статистика продаж по клиентам"""
        from datetime import datetime
        
        logger.info(f"Customer stats request params: {request.GET}")
        
        # Получаем параметры фильтрации
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        
        # Фильтруем по периоду, если указан
        queryset = Sale.objects.all()
        logger.info(f"Total sales count: {queryset.count()}")
        
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                
                period_start = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
                period_end = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
                
                queryset = queryset.filter(created_at__range=[period_start, period_end])
                logger.info(f"Filtered sales count: {queryset.count()}")
            except ValueError:
                return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}, status=400)
        
        # Статистика по клиентам
        customer_stats = (
            queryset.exclude(customer__isnull=True)
            .values('customer__name')
            .annotate(
                total_orders=Count('id'),
                total_amount=Sum('total_amount'),
                customer=F('customer__name')
            )
            .order_by('-total_amount')[:20]
        )
        
        logger.info(f"Customer stats count: {customer_stats.count()}")
        logger.info(f"Sample customer stats: {list(customer_stats[:3])}")
        
        # Добавляем rankings и avg_order_value
        for idx, customer in enumerate(customer_stats):
            customer['rank'] = idx + 1
            customer['total_amount'] = float(customer['total_amount']) if customer['total_amount'] else 0.0
            # Вычисляем среднее значение заказа
            customer['avg_order_value'] = customer['total_amount'] / max(customer['total_orders'], 1)
        
        # Топ клиенты по количеству заказов
        top_by_orders = (
            queryset.exclude(customer__isnull=True)
            .values('customer__name')
            .annotate(
                total_orders=Count('id'),
                total_amount=Sum('total_amount'),
                customer=F('customer__name')
            )
            .order_by('-total_orders')[:10]
        )
        
        # Топ клиенты по сумме
        top_by_amount = (
            queryset.exclude(customer__isnull=True)
            .values('customer__name')
            .annotate(
                total_amount=Sum('total_amount'),
                total_orders=Count('id'),
                customer=F('customer__name')
            )
            .order_by('-total_amount')[:10]
        )
        
        for customer in top_by_orders:
            customer['total_amount'] = float(customer['total_amount']) if customer['total_amount'] else 0.0
            
        for customer in top_by_amount:
            customer['total_amount'] = float(customer['total_amount']) if customer['total_amount'] else 0.0
        
        response_data = {
            'customer_stats': list(customer_stats),
            'top_by_orders': list(top_by_orders),
            'top_by_amount': list(top_by_amount),
            'period': {
                'start_date': start_date_param,
                'end_date': end_date_param
            }
        }
        
        logger.info(f"Response data structure: {list(response_data.keys())}")
        return Response(response_data)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'contact_person']
    ordering = ['name']


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all()
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePurchaseSerializer
        return PurchaseSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика закупок"""
        today = timezone.now().date()
        
        stats = {
            'today_count': self.get_queryset().filter(created_at__date=today).count(),
            'today_amount': self.get_queryset().filter(
                created_at__date=today
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
            'total_count': self.get_queryset().count(),
            'total_amount': self.get_queryset().aggregate(
                Sum('total_amount')
            )['total_amount__sum'] or Decimal('0')
        }
        
        return Response(stats)


class DashboardViewSet(viewsets.ViewSet):
    """Дашборд с общей статистикой"""
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Общая статистика для дашборда с поддержкой фильтрации по периоду"""
        from datetime import datetime
        
        # Получаем параметры дат из запроса
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        logger.info(f"Dashboard stats request: start_date={start_date_param}, end_date={end_date_param}")
        
        # Получаем текущую дату в локальном часовом поясе
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # Определяем период для анализа
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                is_period_analysis = True
                logger.info(f"Period analysis: {start_date} to {end_date}")
            except ValueError:
                return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}, status=400)
        else:
            # По умолчанию анализируем сегодняшний день
            start_date = today
            end_date = today
            is_period_analysis = False
            logger.info(f"Today analysis: {start_date}")
        
        # Подсчет красок (не зависит от периода)
        total_paints = Paint.objects.filter(is_active=True).count()
        low_stock_paints = len([
            p for p in Paint.objects.filter(is_active=True) 
            if p.is_low_stock
        ])
        
        # Продажи за период
        period_start = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        period_end = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
        
        period_sales = Sale.objects.filter(created_at__range=[period_start, period_end])
        period_sales_count = period_sales.count()
        period_sales_amount = period_sales.aggregate(
            Sum('total_amount')
        )['total_amount__sum'] or Decimal('0')
        
        logger.info(f"Period sales: count={period_sales_count}, amount={period_sales_amount}")
        
        # Общая стоимость остатков (актуальная на текущий момент)
        total_stock_value = Decimal('0')
        for paint in Paint.objects.filter(is_active=True):
            stock = paint.current_stock
            if stock > 0:
                total_stock_value += stock * paint.selling_price
        
        # Расчет прибыли за период
        period_profit = Decimal('0')
        for sale in period_sales:
            for item in sale.items.all():
                # Прибыль = (Цена продажи - Цена покупки) * Количество
                item_profit = (item.unit_price - item.paint.cost_price) * item.quantity
                period_profit += item_profit
        
        logger.info(f"Period profit: {period_profit}")
        
        # Формируем ответ
        stats = {
            'total_paints': total_paints,
            'low_stock_paints': low_stock_paints,
            'today_sales_count': period_sales_count,  # Используем для совместимости
            'today_sales_amount': period_sales_amount,  # Используем для совместимости
            'today_profit': period_profit,  # Используем для совместимости
            'total_stock_value': total_stock_value,
        }
        
        # Добавляем информацию о периоде, если это не сегодняшний день
        if is_period_analysis:
            stats.update({
                'period_sales_count': period_sales_count,
                'period_sales_amount': period_sales_amount,
                'period_profit': period_profit,
                'start_date': start_date_param,
                'end_date': end_date_param,
            })
        
        logger.info(f"Returning stats: {stats}")
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet для управления клиентами"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['name', 'phone', 'email']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Детальная информация о балансе клиента"""
        customer = self.get_object()
        serializer = CustomerBalanceSerializer(customer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """Список клиентов с долгами"""
        debtors = self.get_queryset().filter(balance__gt=0, is_active=True)
        serializer = self.get_serializer(debtors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def with_prepayment(self, request):
        """Список клиентов с предоплатой"""
        prepaid_customers = self.get_queryset().filter(balance__lt=0, is_active=True)
        serializer = self.get_serializer(prepaid_customers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Добавить платеж для клиента"""
        customer = self.get_object()
        data = request.data.copy()
        data['customer'] = customer.id
        
        serializer = CreatePaymentSerializer(data=data)
        if serializer.is_valid():
            payment = serializer.save()
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet для управления платежами"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'payment_type']
    search_fields = ['customer__name', 'notes']
    ordering = ['-payment_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePaymentSerializer
        return PaymentSerializer

    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        """Платежи по клиенту"""
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'Параметр customer_id обязателен'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = self.get_queryset().filter(customer_id=customer_id)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по платежам"""
        # Получаем текущую дату
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        today_payments = self.get_queryset().filter(payment_date__range=[today_start, today_end])
        
        stats = {
            'today_payments_count': today_payments.count(),
            'today_payments_amount': today_payments.aggregate(
                Sum('amount')
            )['amount__sum'] or Decimal('0'),
            'total_payments_count': self.get_queryset().count(),
            'total_payments_amount': self.get_queryset().aggregate(
                Sum('amount')
            )['amount__sum'] or Decimal('0'),
            'by_payment_type': {}
        }
        
        # Статистика по типам оплаты
        for payment_type, display_name in Payment.PAYMENT_TYPE_CHOICES:
            type_payments = self.get_queryset().filter(payment_type=payment_type)
            stats['by_payment_type'][payment_type] = {
                'display_name': display_name,
                'count': type_payments.count(),
                'amount': type_payments.aggregate(
                    Sum('amount')
                )['amount__sum'] or Decimal('0')
            }
        
        return Response(stats)
