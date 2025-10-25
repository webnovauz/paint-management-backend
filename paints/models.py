from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class PaintCategory(models.Model):
    """Категория красок (масляная, акриловая, водоэмульсионная и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категория краски"
        verbose_name_plural = "Категории красок"
        ordering = ['name']

    def __str__(self):
        return self.name


class Paint(models.Model):
    """Модель краски с поддержкой весовых единиц"""
    UNIT_CHOICES = [
        ('g', 'Граммы'),
        ('kg', 'Килограммы'),
        ('l', 'Литры'),
        ('ml', 'Миллилитры'),
        ('шт', 'Штуки'),
        ('упак', 'Упаковки'),
        ('комп', 'Комплекты'),
        ('м', 'Метры'),
        ('м²', 'Квадратные метры'),
    ]
    
    PRODUCT_TYPE_CHOICES = [
        ('piece', 'Штучный товар'),
        ('measured', 'Метражный товар'),
        ('volume', 'Объёмный товар'),
    ]

    name = models.CharField(max_length=200, verbose_name="Название краски")
    category = models.ForeignKey(
        PaintCategory, 
        on_delete=models.CASCADE, 
        related_name='paints',
        verbose_name="Категория"
    )
    color = models.CharField(max_length=50, verbose_name="Цвет")
    brand = models.CharField(max_length=100, verbose_name="Бренд")
    unit = models.CharField(
        max_length=5, 
        choices=UNIT_CHOICES, 
        default='kg',
        verbose_name="Единица измерения"
    )
    product_type = models.CharField(
        max_length=10,
        choices=PRODUCT_TYPE_CHOICES,
        default='measured',
        verbose_name="Тип товара"
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Себестоимость за единицу"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Цена продажи за единицу"
    )
    density = models.DecimalField(
        max_digits=6, 
        decimal_places=3,
        null=True, 
        blank=True,
        help_text="Плотность в кг/л (для пересчета объема в вес)",
        verbose_name="Плотность (кг/л)"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    sku = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Артикул"
    )
    min_stock_level = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        default=Decimal('0'),
        help_text="Минимальный остаток для уведомления",
        verbose_name="Минимальный остаток"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Краска"
        verbose_name_plural = "Краски"
        ordering = ['name', 'color']
        unique_together = ['name', 'color', 'brand']

    def __str__(self):
        return f"{self.name} - {self.color} ({self.brand})"

    @property
    def current_stock(self):
        """Текущий остаток краски"""
        return self.stock_movements.aggregate(
            total=models.Sum('quantity')
        )['total'] or Decimal('0')

    @property
    def is_low_stock(self):
        """Проверка на низкий остаток"""
        return self.current_stock <= self.min_stock_level

    @property
    def profit_margin(self):
        """Расчет маржи в процентах"""
        if self.selling_price > 0:
            return ((self.selling_price - self.cost_price) / self.selling_price * 100).quantize(Decimal('0.01'))
        return Decimal('0')

    @property
    def profit_per_unit(self):
        """Прибыль с единицы товара"""
        return (self.selling_price - self.cost_price).quantize(Decimal('0.01'))


class StockMovement(models.Model):
    """Движение товаров (поступления и расходы)"""
    MOVEMENT_TYPES = [
        ('in', 'Поступление'),
        ('out', 'Расход'),
        ('adjustment', 'Корректировка'),
    ]

    paint = models.ForeignKey(
        Paint, 
        on_delete=models.CASCADE, 
        related_name='stock_movements',
        verbose_name="Краска"
    )
    movement_type = models.CharField(
        max_length=20, 
        choices=MOVEMENT_TYPES,
        verbose_name="Тип движения"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        verbose_name="Количество"
    )
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        verbose_name="Цена за единицу"
    )
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True, 
        blank=True,
        verbose_name="Общая стоимость"
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Создано пользователем"
    )

    class Meta:
        verbose_name = "Движение товара"
        verbose_name_plural = "Движения товаров"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.paint.name} - {self.get_movement_type_display()}: {self.quantity} {self.paint.unit}"

    def save(self, *args, **kwargs):
        # Автоматический расчет общей стоимости
        if self.price_per_unit and self.quantity:
            self.total_cost = self.price_per_unit * abs(self.quantity)
        
        # Для расходов количество должно быть отрицательным
        if self.movement_type == 'out' and self.quantity > 0:
            self.quantity = -self.quantity
        
        super().save(*args, **kwargs)


class Customer(models.Model):
    """Модель клиента для учета задолженности"""
    name = models.CharField(max_length=200, verbose_name="Имя клиента")
    phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Телефон"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )
    address = models.TextField(
        blank=True,
        verbose_name="Адрес"
    )
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Баланс",
        help_text="Положительное значение - долг клиента, отрицательное - предоплата"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone if self.phone else 'без телефона'})"

    @property
    def has_debt(self):
        """Есть ли у клиента долг"""
        return self.balance > 0

    @property
    def has_prepayment(self):
        """Есть ли у клиента предоплата"""
        return self.balance < 0

    @property
    def debt_amount(self):
        """Сумма долга (только положительные значения)"""
        return max(self.balance, Decimal('0'))

    @property
    def prepayment_amount(self):
        """Сумма предоплаты (только положительные значения)"""
        return abs(min(self.balance, Decimal('0')))


class Payment(models.Model):
    """Модель платежа клиента"""
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Наличные'),
        ('transfer', 'Банковский перевод'),
        ('card', 'Оплата картой'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Клиент"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Сумма платежа"
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        default='cash',
        verbose_name="Тип оплаты"
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата платежа"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Примечания"
    )
    created_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Создано пользователем"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.customer.name} - {self.amount}₽ ({self.get_payment_type_display()})"

    def save(self, *args, **kwargs):
        """Обновляем баланс клиента при сохранении платежа"""
        is_new = self.pk is None
        
        if is_new:
            # При создании нового платежа уменьшаем долг клиента
            super().save(*args, **kwargs)
            self.customer.balance -= self.amount
            self.customer.save()
        else:
            # При обновлении существующего платежа
            old_payment = Payment.objects.get(pk=self.pk)
            difference = self.amount - old_payment.amount
            
            super().save(*args, **kwargs)
            self.customer.balance -= difference
            self.customer.save()

    def delete(self, *args, **kwargs):
        """При удалении платежа возвращаем сумму к балансу клиента"""
        self.customer.balance += self.amount
        self.customer.save()
        super().delete(*args, **kwargs)


class Sale(models.Model):
    """Продажа красок с поддержкой клиентов и типов оплаты"""
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Наличные'),
        ('transfer', 'Банковский перевод'),
        ('card', 'Оплата картой'),
        ('debt', 'В долг'),
    ]

    sale_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Номер продажи"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Клиент"
    )
    customer_name = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="Имя покупателя",
        help_text="Заполняется автоматически при выборе клиента"
    )
    customer_phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Телефон покупателя",
        help_text="Заполняется автоматически при выборе клиента"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Общая сумма"
    )
    paid_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Оплачено"
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        default='cash',
        verbose_name="Тип оплаты"
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        ordering = ['-created_at']

    def __str__(self):
        return f"Продажа №{self.sale_number} от {self.created_at.date()}"

    def save(self, *args, **kwargs):
        # Автоматическое создание номера продажи
        if not self.sale_number:
            from datetime import datetime
            self.sale_number = f"S{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Автоматическое заполнение данных клиента
        if self.customer and not self.customer_name:
            self.customer_name = self.customer.name
            self.customer_phone = self.customer.phone
        
        # Если не указана оплаченная сумма, считаем что оплачено полностью
        if self.paid_amount == 0 and self.payment_type != 'debt':
            self.paid_amount = self.total_amount
        
        super().save(*args, **kwargs)

    @property
    def debt_amount(self):
        """Сумма долга по продаже"""
        return max(self.total_amount - self.paid_amount, Decimal('0'))

    @property
    def is_fully_paid(self):
        """Полностью ли оплачена продажа"""
        return self.paid_amount >= self.total_amount

    @property
    def payment_status(self):
        """Статус оплаты"""
        if self.is_fully_paid:
            return "Оплачено"
        elif self.paid_amount > 0:
            return "Частично оплачено"
        else:
            return "Не оплачено"


class SaleItem(models.Model):
    """Позиция в продаже"""
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Продажа"
    )
    paint = models.ForeignKey(
        Paint, 
        on_delete=models.CASCADE,
        verbose_name="Краска"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Количество"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Цена за единицу"
    )
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Общая стоимость"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Позиция продажи"
        verbose_name_plural = "Позиции продаж"

    def __str__(self):
        return f"{self.paint.name} - {self.quantity} {self.paint.unit}"

    def save(self, *args, **kwargs):
        # Автоматический расчет общей стоимости
        self.total_price = self.unit_price * self.quantity
        
        # Создание записи о движении товара
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Создаем запись о расходе товара
            StockMovement.objects.create(
                paint=self.paint,
                movement_type='out',
                quantity=self.quantity,
                price_per_unit=self.unit_price,
                notes=f"Продажа №{self.sale.sale_number}"
            )
            
            # Обновляем общую сумму продажи
            self.sale.total_amount = self.sale.items.aggregate(
                total=models.Sum('total_price')
            )['total'] or Decimal('0')
            self.sale.save()


class Supplier(models.Model):
    """Поставщик красок"""
    name = models.CharField(max_length=200, verbose_name="Название поставщика")
    contact_person = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Контактное лицо"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Адрес")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']

    def __str__(self):
        return self.name


class Purchase(models.Model):
    """Закупка красок"""
    purchase_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Номер закупки"
    )
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE,
        verbose_name="Поставщик"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Общая сумма"
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Закупка"
        verbose_name_plural = "Закупки"
        ordering = ['-created_at']

    def __str__(self):
        return f"Закупка №{self.purchase_number} от {self.supplier.name}"

    def save(self, *args, **kwargs):
        # Автоматическое создание номера закупки
        if not self.purchase_number:
            from datetime import datetime
            self.purchase_number = f"P{datetime.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)


class PurchaseItem(models.Model):
    """Позиция в закупке"""
    purchase = models.ForeignKey(
        Purchase, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Закупка"
    )
    paint = models.ForeignKey(
        Paint, 
        on_delete=models.CASCADE,
        verbose_name="Краска"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Количество"
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Стоимость за единицу"
    )
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Общая стоимость"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Позиция закупки"
        verbose_name_plural = "Позиции закупок"

    def __str__(self):
        return f"{self.paint.name} - {self.quantity} {self.paint.unit}"

    def save(self, *args, **kwargs):
        # Автоматический расчет общей стоимости
        self.total_cost = self.unit_cost * self.quantity
        
        # Создание записи о поступлении товара
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Создаем запись о поступлении товара
            StockMovement.objects.create(
                paint=self.paint,
                movement_type='in',
                quantity=self.quantity,
                price_per_unit=self.unit_cost,
                notes=f"Закупка №{self.purchase.purchase_number}"
            )
            
            # Обновляем общую сумму закупки
            self.purchase.total_amount = self.purchase.items.aggregate(
                total=models.Sum('total_cost')
            )['total'] or Decimal('0')
            self.purchase.save()


class PriceHistory(models.Model):
    """История изменения цен красок"""
    paint = models.ForeignKey(
        Paint, 
        on_delete=models.CASCADE, 
        related_name='price_history',
        verbose_name="Краска"
    )
    old_cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        verbose_name="Предыдущая себестоимость"
    )
    new_cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Новая себестоимость"
    )
    old_selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        verbose_name="Предыдущая цена продажи"
    )
    new_selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Новая цена продажи"
    )
    changed_by = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Изменено пользователем"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Причина изменения"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "История изменения цен"
        verbose_name_plural = "История изменения цен"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.paint.name} - {self.created_at.date()}"

    @property
    def cost_price_change_percent(self):
        """Процентное изменение себестоимости"""
        if self.old_cost_price and self.old_cost_price > 0:
            return ((self.new_cost_price - self.old_cost_price) / self.old_cost_price * 100).quantize(Decimal('0.01'))
        return Decimal('0')

    @property
    def selling_price_change_percent(self):
        """Процентное изменение цены продажи"""
        if self.old_selling_price and self.old_selling_price > 0:
            return ((self.new_selling_price - self.old_selling_price) / self.old_selling_price * 100).quantize(Decimal('0.01'))
        return Decimal('0')


