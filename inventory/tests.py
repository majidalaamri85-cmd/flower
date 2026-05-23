from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Product, StockMovement, Supplier


class SupplierModelTests(TestCase):
	def test_supplier_string_representation(self):
		supplier = Supplier.objects.create(name='المورد الأول', phone='0500000000')
		self.assertEqual(str(supplier), 'المورد الأول')


class ProductModelTests(TestCase):
	def test_product_generates_sku_on_save(self):
		product = Product.objects.create(
			name='ورد جوري',
			type='flower',
			purchase_price=Decimal('10.00'),
			selling_price=Decimal('15.00'),
		)

		self.assertTrue(product.sku.startswith('FL'))

	def test_profit_margin_calculation(self):
		product = Product.objects.create(
			name='شوكولاته فاخرة',
			type='chocolate',
			purchase_price=Decimal('20.00'),
			selling_price=Decimal('30.00'),
		)

		self.assertEqual(product.profit_margin, Decimal('50'))

	def test_is_expiring_soon_for_flower(self):
		harvest_date = (timezone.now() - timedelta(hours=47)).date()
		product = Product.objects.create(
			name='ورد أبيض',
			type='flower',
			harvest_date=harvest_date,
			shelf_life_hours=48,
			purchase_price=Decimal('8.00'),
			selling_price=Decimal('12.00'),
		)

		self.assertTrue(product.is_expiring_soon)


class StockMovementModelTests(TestCase):
	def test_stock_movement_updates_product_quantity(self):
		product = Product.objects.create(
			name='باقة ورد',
			type='flower',
			quantity=Decimal('0'),
			purchase_price=Decimal('40.00'),
			selling_price=Decimal('60.00'),
		)

		StockMovement.objects.create(product=product, quantity=Decimal('10'), movement_type='in')
		product.refresh_from_db()
		self.assertEqual(product.quantity, Decimal('10'))

		StockMovement.objects.create(product=product, quantity=Decimal('4'), movement_type='out')
		product.refresh_from_db()
		self.assertEqual(product.quantity, Decimal('6'))

	def test_stock_movement_rejects_negative_stock(self):
		product = Product.objects.create(
			name='Limited Box',
			type='chocolate',
			quantity=Decimal('1'),
			purchase_price=Decimal('4.00'),
			selling_price=Decimal('8.00'),
		)

		with self.assertRaises(ValidationError):
			StockMovement.objects.create(product=product, quantity=Decimal('2'), movement_type='out')

		product.refresh_from_db()
		self.assertEqual(product.quantity, Decimal('1'))
