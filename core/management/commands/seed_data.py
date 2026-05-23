from datetime import datetime, timedelta
from decimal import Decimal
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Expense, ExpenseCategory
from core.models import Category, ShopSettings
from inventory.models import Product, StockMovement, Supplier
from sales.models import BundleOffer, Customer, Sale, SaleItem


class Command(BaseCommand):
    help = 'تعبئة قاعدة البيانات ببيانات تجريبية للمنتجات والمصروفات والعملاء والمبيعات'

    def handle(self, *args, **kwargs):
        self.stdout.write('🚀 بدء تعبئة قاعدة البيانات...')

        self.setup_shop_settings()
        self.setup_categories()
        self.setup_suppliers()
        self.setup_products()
        self.setup_customers()
        self.setup_expense_categories()
        self.setup_expenses()
        self.setup_past_sales()
        self.setup_bundles()

        self.stdout.write(self.style.SUCCESS('✅ تم تعبئة قاعدة البيانات بنجاح!'))

    def setup_shop_settings(self):
        _, created = ShopSettings.objects.get_or_create(
            pk=1,
            defaults={
                'shop_name': 'روز وشوكولاته',
                'phone': '+966551234567',
                'email': 'info@roseshocolate.com',
                'address': 'الرياض - المملكة العربية السعودية',
                'tax_number': '1234567890',
                'currency_symbol': 'ريال',
            },
        )
        if created:
            self.stdout.write('✓ تم إنشاء إعدادات المحل')

    def setup_categories(self):
        category_rows = [
            {'name': 'ورود حمراء', 'type': 'flower'},
            {'name': 'ورود بيضاء', 'type': 'flower'},
            {'name': 'ورود مختلطة', 'type': 'flower'},
            {'name': 'باقات', 'type': 'flower'},
            {'name': 'شوكولاته داكنة', 'type': 'chocolate'},
            {'name': 'شوكولاته بالحليب', 'type': 'chocolate'},
            {'name': 'شوكولاته بيضاء', 'type': 'chocolate'},
            {'name': 'شوكولاته فاخرة', 'type': 'chocolate'},
            {'name': 'باقات هدايا', 'type': 'gift'},
            {'name': 'صناديق هدايا', 'type': 'gift'},
        ]

        for row in category_rows:
            category, created = Category.objects.get_or_create(
                name=row['name'],
                defaults={'type': row['type'], 'is_active': True},
            )
            if created:
                self.stdout.write(f'✓ تم إنشاء تصنيف: {category.name}')

    def setup_suppliers(self):
        supplier_rows = [
            {'name': 'مزرعة الورد الهولندي', 'phone': '+3112345678', 'email': 'info@dutchroses.nl'},
            {'name': 'شوكولاته بلجيكا', 'phone': '+3287654321', 'email': 'sales@belgianchoco.be'},
            {'name': 'هدايا فاخرة', 'phone': '+966512345678', 'email': 'info@luxurygifts.com'},
            {'name': 'مورد محلي للورود', 'phone': '+966554433221', 'email': 'local@flowers.sa'},
        ]

        for row in supplier_rows:
            supplier, created = Supplier.objects.get_or_create(
                name=row['name'],
                defaults={
                    'phone': row['phone'],
                    'email': row['email'],
                    'is_active': True,
                    'address': '',
                    'contact_person': '',
                },
            )
            if created:
                self.stdout.write(f'✓ تم إنشاء مورد: {supplier.name}')

    def setup_products(self):
        today = timezone.localdate()
        product_rows = [
            {
                'name': 'ورد أحمر طبيعي',
            'sku': 'SEED-FL-0001',
                'type': 'flower',
                'category_name': 'ورود حمراء',
                'quantity': Decimal('100'),
                'min_stock': Decimal('20'),
                'purchase_price': Decimal('15'),
                'selling_price': Decimal('45'),
                'harvest_date': today - timedelta(days=1),
                'shelf_life_hours': 72,
                'is_fresh': True,
            },
            {
                'name': 'ورد أبيض فاخر',
                'sku': 'SEED-FL-0002',
                'type': 'flower',
                'category_name': 'ورود بيضاء',
                'quantity': Decimal('80'),
                'min_stock': Decimal('15'),
                'purchase_price': Decimal('18'),
                'selling_price': Decimal('55'),
                'harvest_date': today,
                'shelf_life_hours': 72,
                'is_fresh': True,
            },
            {
                'name': 'باقة ورد مختلط (12 وردة)',
                'sku': 'SEED-FL-0003',
                'type': 'flower',
                'category_name': 'باقات',
                'quantity': Decimal('50'),
                'min_stock': Decimal('10'),
                'purchase_price': Decimal('45'),
                'selling_price': Decimal('120'),
                'harvest_date': today,
                'shelf_life_hours': 48,
                'is_fresh': True,
            },
            {
                'name': 'توليب هولندي',
                'sku': 'SEED-FL-0004',
                'type': 'flower',
                'category_name': 'ورود مختلطة',
                'quantity': Decimal('60'),
                'min_stock': Decimal('12'),
                'purchase_price': Decimal('20'),
                'selling_price': Decimal('65'),
                'harvest_date': today,
                'shelf_life_hours': 60,
                'is_fresh': True,
            },
            {
                'name': 'شوكولاته بلجيكية داكنة 70%',
                'sku': 'SEED-CH-0001',
                'type': 'chocolate',
                'category_name': 'شوكولاته داكنة',
                'quantity': Decimal('200'),
                'min_stock': Decimal('30'),
                'purchase_price': Decimal('25'),
                'selling_price': Decimal('65'),
                'storage_temp': Decimal('18.0'),
                'is_fresh': False,
            },
            {
                'name': 'شوكولاته بالحليب مع بندق',
                'sku': 'SEED-CH-0002',
                'type': 'chocolate',
                'category_name': 'شوكولاته بالحليب',
                'quantity': Decimal('150'),
                'min_stock': Decimal('25'),
                'purchase_price': Decimal('22'),
                'selling_price': Decimal('55'),
                'storage_temp': Decimal('18.0'),
                'is_fresh': False,
            },
            {
                'name': 'شوكولاته بيضاء بتوت بري',
                'sku': 'SEED-CH-0003',
                'type': 'chocolate',
                'category_name': 'شوكولاته بيضاء',
                'quantity': Decimal('120'),
                'min_stock': Decimal('20'),
                'purchase_price': Decimal('28'),
                'selling_price': Decimal('75'),
                'storage_temp': Decimal('18.0'),
                'is_fresh': False,
            },
            {
                'name': 'صندوق شوكولاته فاخر 24 قطعة',
                'sku': 'SEED-CH-0004',
                'type': 'chocolate',
                'category_name': 'شوكولاته فاخرة',
                'quantity': Decimal('60'),
                'min_stock': Decimal('10'),
                'purchase_price': Decimal('80'),
                'selling_price': Decimal('180'),
                'storage_temp': Decimal('18.0'),
                'is_seasonal': True,
                'is_fresh': False,
            },
            {
                'name': 'باقة هدية + شوكولاته',
                'sku': 'SEED-GF-0001',
                'type': 'gift',
                'category_name': 'باقات هدايا',
                'quantity': Decimal('40'),
                'min_stock': Decimal('8'),
                'purchase_price': Decimal('60'),
                'selling_price': Decimal('150'),
                'is_fresh': False,
            },
            {
                'name': 'دبدوب + شوكولاته',
                'sku': 'SEED-GF-0002',
                'type': 'gift',
                'category_name': 'صناديق هدايا',
                'quantity': Decimal('30'),
                'min_stock': Decimal('5'),
                'purchase_price': Decimal('45'),
                'selling_price': Decimal('120'),
                'is_fresh': False,
            },
        ]

        for row in product_rows:
            category = Category.objects.filter(name=row.pop('category_name')).first()
            if not category:
                continue
            product, created = Product.objects.get_or_create(
                name=row['name'],
                defaults={
                    **row,
                    'category': category,
                    'is_active': True,
                },
            )
            if created:
                self.stdout.write(f'✓ تم إنشاء منتج: {product.name}')

    def setup_customers(self):
        customer_rows = [
            {'name': 'أحمد محمد', 'phone': '0501234567', 'email': 'ahmed@email.com', 'is_vip': True},
            {'name': 'سارة عبدالله', 'phone': '0557654321', 'email': 'sara@email.com', 'is_vip': True},
            {'name': 'محمد علي', 'phone': '0531122334', 'email': 'mohamed@email.com', 'is_vip': False},
            {'name': 'نورة خالد', 'phone': '0589988776', 'email': 'noura@email.com', 'is_vip': True},
            {'name': 'عبدالله فهد', 'phone': '0566655443', 'email': 'abdullah@email.com', 'is_vip': False},
        ]

        for row in customer_rows:
            customer, created = Customer.objects.get_or_create(
                phone=row['phone'],
                defaults={
                    'name': row['name'],
                    'email': row['email'],
                    'is_vip': row['is_vip'],
                },
            )
            if created:
                self.stdout.write(f'✓ تم إنشاء عميل: {customer.name}')

    def setup_expense_categories(self):
        rows = [
            {'name': 'إيجار المحل', 'category_type': 'rent', 'icon': 'fas fa-building', 'color': 'primary'},
            {'name': 'رواتب الموظفين', 'category_type': 'salaries', 'icon': 'fas fa-users', 'color': 'success'},
            {'name': 'كهرباء وماء', 'category_type': 'utilities', 'icon': 'fas fa-bolt', 'color': 'warning'},
            {'name': 'شراء ورد طازج', 'category_type': 'supplies', 'icon': 'fas fa-leaf', 'color': 'danger'},
            {'name': 'شراء شوكولاته', 'category_type': 'supplies', 'icon': 'fas fa-candy-cane', 'color': 'info'},
            {'name': 'توصيل طلبات', 'category_type': 'transport', 'icon': 'fas fa-truck', 'color': 'primary'},
            {'name': 'إعلانات وتسويق', 'category_type': 'marketing', 'icon': 'fas fa-ad', 'color': 'warning'},
        ]
        for row in rows:
            ExpenseCategory.objects.get_or_create(name=row['name'], defaults=row)

    def setup_expenses(self):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()

        rows = [
            {'category': 'إيجار المحل', 'amount': Decimal('5000'), 'description': 'إيجار شهر', 'days_ago': 30},
            {'category': 'رواتب الموظفين', 'amount': Decimal('8000'), 'description': 'رواتب شهر', 'days_ago': 30},
            {'category': 'كهرباء وماء', 'amount': Decimal('800'), 'description': 'فواتير خدمات', 'days_ago': 25},
            {'category': 'شراء ورد طازج', 'amount': Decimal('2000'), 'description': 'شراء ورد من المزرعة', 'days_ago': 20},
            {'category': 'شراء شوكولاته', 'amount': Decimal('1500'), 'description': 'شوكولاته بلجيكية', 'days_ago': 18},
            {'category': 'توصيل طلبات', 'amount': Decimal('400'), 'description': 'توصيل الطلبات', 'days_ago': 15},
            {'category': 'إعلانات وتسويق', 'amount': Decimal('1000'), 'description': 'إعلانات فيسبوك', 'days_ago': 10},
        ]

        for row in rows:
            category = ExpenseCategory.objects.filter(name=row['category']).first()
            if not category:
                continue

            expense_date = timezone.localdate() - timedelta(days=row['days_ago'])
            expense, created = Expense.objects.get_or_create(
                category=category,
                amount=row['amount'],
                description=row['description'],
                expense_date=expense_date,
                defaults={
                    'created_by': admin_user,
                    'payment_method': 'cash',
                },
            )
            if created:
                self.stdout.write(f'✓ تم إنشاء مصروف: {expense.description}')

    def setup_past_sales(self):
        # Skip generating duplicate synthetic sales on repeated runs.
        if Sale.objects.filter(notes='بيع تجريبي').exists():
            self.stdout.write('• المبيعات التجريبية موجودة مسبقا')
            return

        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin_user:
            admin_user = User.objects.create_user('seed_operator', email='seed_operator@example.com')
            admin_user.set_unusable_password()
            admin_user.is_staff = True
            admin_user.save(update_fields=['password', 'is_staff'])

        products = list(Product.objects.filter(is_active=True))
        customers = list(Customer.objects.all())
        if not products:
            return

        random.seed(42)

        for day in range(30, 0, -1):
            sale_date = timezone.localdate() - timedelta(days=day)
            num_sales = random.randint(2, 5)

            for _ in range(num_sales):
                selected_products = random.sample(products, min(random.randint(1, 3), len(products)))

                subtotal = Decimal('0')
                item_rows = []
                for product in selected_products:
                    quantity = Decimal(str(random.randint(1, 2)))
                    total = product.selling_price * quantity
                    subtotal += total
                    item_rows.append((product, quantity, product.selling_price, total))

                discount = subtotal * Decimal('0.10') if random.random() > 0.7 else Decimal('0')
                total = subtotal - discount
                customer = random.choice(customers) if customers and random.random() > 0.3 else None
                payment_method = random.choice(['cash', 'card', 'mada'])

                sale = Sale.objects.create(
                    invoice_number='',
                    customer=customer,
                    employee=admin_user,
                    subtotal=subtotal,
                    discount=discount,
                    tax=Decimal('0'),
                    total=total,
                    payment_method=payment_method,
                    paid_amount=total,
                    notes='بيع تجريبي',
                )

                desired_created_at = timezone.make_aware(
                    datetime.combine(sale_date, datetime.min.time())
                ) + timedelta(hours=random.randint(10, 20))
                Sale.objects.filter(pk=sale.pk).update(created_at=desired_created_at)

                for product, quantity, unit_price, line_total in item_rows:
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total=line_total,
                    )
                    StockMovement.objects.create(
                        product=product,
                        quantity=quantity,
                        movement_type='out',
                        reference=f'SALE-{sale.invoice_number}',
                        notes=f'بيع - فاتورة {sale.invoice_number}',
                        created_by=admin_user,
                    )

                if customer:
                    customer.total_purchases = (customer.total_purchases or Decimal('0')) + total
                    customer.last_purchase_date = desired_created_at
                    customer.save(update_fields=['total_purchases', 'last_purchase_date'])

        self.stdout.write('✓ تم إنشاء المبيعات السابقة')

    def setup_bundles(self):
        flower = Product.objects.filter(type='flower', is_active=True).first()
        chocolate = Product.objects.filter(type='chocolate', is_active=True).first()
        if not flower or not chocolate:
            return

        bundle, created = BundleOffer.objects.get_or_create(
            name='عرض الحب',
            defaults={
                'flower_product': flower,
                'chocolate_product': chocolate,
                'flower_quantity': Decimal('1'),
                'chocolate_quantity': Decimal('1'),
                'regular_price': flower.selling_price + chocolate.selling_price,
                'bundle_price': (flower.selling_price + chocolate.selling_price) * Decimal('0.85'),
                'start_date': timezone.localdate(),
                'end_date': timezone.localdate() + timedelta(days=30),
                'is_active': True,
            },
        )
        if created:
            self.stdout.write(f'✓ تم إنشاء عرض مجمع: {bundle.name}')
