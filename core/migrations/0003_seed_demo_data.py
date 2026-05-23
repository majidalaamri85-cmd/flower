from datetime import datetime, timedelta
from decimal import Decimal
import random

from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.utils import timezone


def seed_demo_data(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    ShopSettings = apps.get_model('core', 'ShopSettings')
    Supplier = apps.get_model('inventory', 'Supplier')
    Product = apps.get_model('inventory', 'Product')
    Customer = apps.get_model('sales', 'Customer')
    Sale = apps.get_model('sales', 'Sale')
    SaleItem = apps.get_model('sales', 'SaleItem')
    BundleOffer = apps.get_model('sales', 'BundleOffer')
    ExpenseCategory = apps.get_model('accounts', 'ExpenseCategory')
    Expense = apps.get_model('accounts', 'Expense')
    User = apps.get_model('auth', 'User')

    ShopSettings.objects.get_or_create(
        pk=1,
        defaults={
            'shop_name': 'Roots Flowers Demo',
            'phone': '+966500000000',
            'email': 'info@example.com',
            'address': 'Riyadh',
            'tax_number': '1234567890',
            'currency_symbol': 'SAR',
        },
    )

    category_rows = [
        ('Red Roses', 'flower'),
        ('White Roses', 'flower'),
        ('Mixed Flowers', 'flower'),
        ('Bouquets', 'flower'),
        ('Dark Chocolate', 'chocolate'),
        ('Milk Chocolate', 'chocolate'),
        ('White Chocolate', 'chocolate'),
        ('Luxury Chocolate', 'chocolate'),
        ('Gift Bouquets', 'gift'),
        ('Gift Boxes', 'gift'),
    ]
    for name, type_value in category_rows:
        Category.objects.get_or_create(name=name, defaults={'type': type_value, 'is_active': True})

    supplier_rows = [
        ('Dutch Rose Farm', '+3112345678', 'info@dutchroses.example'),
        ('Belgian Chocolate Co', '+3287654321', 'sales@belgianchoco.example'),
        ('Luxury Gifts', '+966512345678', 'info@luxurygifts.example'),
        ('Local Flower Supplier', '+966554433221', 'local@flowers.example'),
    ]
    for name, phone, email in supplier_rows:
        Supplier.objects.get_or_create(
            name=name,
            defaults={'phone': phone, 'email': email, 'is_active': True, 'address': '', 'contact_person': ''},
        )

    today = timezone.localdate()
    product_rows = [
        ('SEED-FL-0001', 'Red Rose Stem', 'flower', 'Red Roses', '100', '20', '15', '45', True),
        ('SEED-FL-0002', 'Premium White Rose', 'flower', 'White Roses', '80', '15', '18', '55', True),
        ('SEED-FL-0003', 'Mixed Bouquet 12 Stems', 'flower', 'Bouquets', '50', '10', '45', '120', True),
        ('SEED-FL-0004', 'Dutch Tulip', 'flower', 'Mixed Flowers', '60', '12', '20', '65', True),
        ('SEED-CH-0001', 'Belgian Dark Chocolate 70%', 'chocolate', 'Dark Chocolate', '200', '30', '25', '65', False),
        ('SEED-CH-0002', 'Milk Chocolate with Hazelnut', 'chocolate', 'Milk Chocolate', '150', '25', '22', '55', False),
        ('SEED-CH-0003', 'White Chocolate with Berries', 'chocolate', 'White Chocolate', '120', '20', '28', '75', False),
        ('SEED-CH-0004', 'Luxury Chocolate Box 24 pcs', 'chocolate', 'Luxury Chocolate', '60', '10', '80', '180', False),
        ('SEED-GF-0001', 'Gift Bouquet with Chocolate', 'gift', 'Gift Bouquets', '40', '8', '60', '150', False),
        ('SEED-GF-0002', 'Gift Box with Chocolate', 'gift', 'Gift Boxes', '30', '5', '45', '120', False),
    ]
    for sku, name, type_value, category_name, quantity, min_stock, purchase_price, selling_price, is_fresh in product_rows:
        category = Category.objects.filter(name=category_name).first()
        defaults = {
            'name': name,
            'type': type_value,
            'category': category,
            'quantity': Decimal(quantity),
            'min_stock': Decimal(min_stock),
            'purchase_price': Decimal(purchase_price),
            'selling_price': Decimal(selling_price),
            'is_fresh': is_fresh,
            'is_active': True,
        }
        if type_value == 'flower':
            defaults.update({'harvest_date': today, 'shelf_life_hours': 72})
        else:
            defaults.update({'storage_temp': Decimal('18.0')})
        Product.objects.get_or_create(sku=sku, defaults=defaults)

    customer_rows = [
        ('Ahmed Mohammed', '0501234567', 'ahmed@example.com', True),
        ('Sara Abdullah', '0557654321', 'sara@example.com', True),
        ('Mohammed Ali', '0531122334', 'mohammed@example.com', False),
        ('Noura Khaled', '0589988776', 'noura@example.com', True),
        ('Abdullah Fahad', '0566655443', 'abdullah@example.com', False),
    ]
    for name, phone, email, is_vip in customer_rows:
        Customer.objects.get_or_create(phone=phone, defaults={'name': name, 'email': email, 'is_vip': is_vip})

    expense_category_rows = [
        ('Rent', 'rent', 'fas fa-building', 'primary'),
        ('Salaries', 'salaries', 'fas fa-users', 'success'),
        ('Utilities', 'utilities', 'fas fa-bolt', 'warning'),
        ('Fresh Flower Purchase', 'supplies', 'fas fa-leaf', 'danger'),
        ('Chocolate Purchase', 'supplies', 'fas fa-candy-cane', 'info'),
        ('Delivery', 'transport', 'fas fa-truck', 'primary'),
        ('Marketing', 'marketing', 'fas fa-ad', 'warning'),
    ]
    for name, category_type, icon, color in expense_category_rows:
        ExpenseCategory.objects.get_or_create(
            name=name,
            defaults={'category_type': category_type, 'icon': icon, 'color': color},
        )

    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_user:
        admin_user = User.objects.create(
            username='seed_operator',
            email='seed_operator@example.com',
            is_staff=True,
            password=make_password(None),
        )

    expense_rows = [
        ('Rent', '5000', 'Monthly shop rent', 30),
        ('Salaries', '8000', 'Monthly salaries', 30),
        ('Utilities', '800', 'Utility bills', 25),
        ('Fresh Flower Purchase', '2000', 'Fresh flower supply', 20),
        ('Chocolate Purchase', '1500', 'Belgian chocolate supply', 18),
        ('Delivery', '400', 'Order delivery costs', 15),
        ('Marketing', '1000', 'Social media campaign', 10),
    ]
    for category_name, amount, description, days_ago in expense_rows:
        category = ExpenseCategory.objects.filter(name=category_name).first()
        Expense.objects.get_or_create(
            category=category,
            amount=Decimal(amount),
            description=description,
            expense_date=today - timedelta(days=days_ago),
            defaults={'created_by': admin_user, 'payment_method': 'cash'},
        )

    if not Sale.objects.filter(notes='Demo sale').exists():
        products = list(Product.objects.filter(is_active=True))
        customers = list(Customer.objects.all())
        random.seed(42)
        invoice_seq = 1
        for day in range(30, 0, -1):
            sale_date = today - timedelta(days=day)
            for _ in range(random.randint(2, 5)):
                selected_products = random.sample(products, min(random.randint(1, 3), len(products)))
                subtotal = Decimal('0')
                item_rows = []
                for product in selected_products:
                    quantity = Decimal(str(random.randint(1, 2)))
                    line_total = product.selling_price * quantity
                    subtotal += line_total
                    item_rows.append((product, quantity, product.selling_price, line_total))

                discount = subtotal * Decimal('0.10') if random.random() > 0.7 else Decimal('0')
                total = subtotal - discount
                invoice_number = f"INV-{sale_date:%Y%m%d}-{invoice_seq:04d}"
                invoice_seq += 1
                sale = Sale.objects.create(
                    invoice_number=invoice_number,
                    customer=random.choice(customers) if customers and random.random() > 0.3 else None,
                    employee=admin_user,
                    subtotal=subtotal,
                    discount=discount,
                    tax=Decimal('0'),
                    total=total,
                    payment_method=random.choice(['cash', 'card', 'mada']),
                    paid_amount=total,
                    notes='Demo sale',
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

    flower = Product.objects.filter(type='flower', is_active=True).first()
    chocolate = Product.objects.filter(type='chocolate', is_active=True).first()
    if flower and chocolate:
        BundleOffer.objects.get_or_create(
            name='Love Bundle',
            defaults={
                'flower_product': flower,
                'chocolate_product': chocolate,
                'flower_quantity': Decimal('1'),
                'chocolate_quantity': Decimal('1'),
                'regular_price': flower.selling_price + chocolate.selling_price,
                'bundle_price': (flower.selling_price + chocolate.selling_price) * Decimal('0.85'),
                'start_date': today,
                'end_date': today + timedelta(days=30),
                'is_active': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('accounts', '0002_alter_expense_options_alter_expensecategory_options_and_more'),
        ('inventory', '0001_initial'),
        ('sales', '0002_offlinesalequeue'),
        ('core', '0002_alter_shopsettings_shop_name'),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, migrations.RunPython.noop),
    ]
