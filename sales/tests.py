from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product

from .models import BundleOffer, Sale, SaleItem


class SaleModelTests(TestCase):
	def test_sale_generates_invoice_number_and_change_amount(self):
		sale = Sale.objects.create(
			invoice_number='',
			subtotal=Decimal('100.00'),
			discount=Decimal('10.00'),
			tax=Decimal('5.00'),
			total=Decimal('95.00'),
			payment_method='cash',
			paid_amount=Decimal('100.00'),
		)

		self.assertTrue(sale.invoice_number.startswith('INV-'))
		self.assertEqual(sale.change_amount, Decimal('5.00'))


class SaleItemModelTests(TestCase):
	def test_sale_item_calculates_total(self):
		product = Product.objects.create(
			name='شوكولاته',
			type='chocolate',
			purchase_price=Decimal('10.00'),
			selling_price=Decimal('20.00'),
		)
		sale = Sale.objects.create(
			invoice_number='',
			subtotal=Decimal('60.00'),
			total=Decimal('60.00'),
			paid_amount=Decimal('60.00'),
		)

		item = SaleItem.objects.create(
			sale=sale,
			product=product,
			quantity=Decimal('3'),
			unit_price=Decimal('20.00'),
			total=Decimal('0'),
		)

		self.assertEqual(item.total, Decimal('60.00'))


class BundleOfferModelTests(TestCase):
	def test_bundle_savings_property(self):
		flower = Product.objects.create(
			name='ورد موسمي',
			type='flower',
			purchase_price=Decimal('15.00'),
			selling_price=Decimal('25.00'),
		)
		chocolate = Product.objects.create(
			name='علبة شوكولاته',
			type='chocolate',
			purchase_price=Decimal('20.00'),
			selling_price=Decimal('35.00'),
		)

		bundle = BundleOffer.objects.create(
			name='عرض الربيع',
			flower_product=flower,
			chocolate_product=chocolate,
			flower_quantity=Decimal('1'),
			chocolate_quantity=Decimal('1'),
			bundle_price=Decimal('50.00'),
			regular_price=Decimal('60.00'),
			start_date='2026-01-01',
			end_date='2026-12-31',
		)

		self.assertEqual(bundle.savings, Decimal('10.00'))


class BarcodeSearchTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='cashier', password='pass12345')
		self.client.force_login(self.user)

	def test_search_by_barcode_returns_product(self):
		product = Product.objects.create(
			name='Barcode Rose',
			type='flower',
			sku='SKU-BAR-1',
			barcode='123456789012',
			quantity=Decimal('5'),
			purchase_price=Decimal('10.00'),
			selling_price=Decimal('15.00'),
		)

		response = self.client.get(reverse('sales:search_by_barcode'), {'barcode': product.barcode})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['success'])
		self.assertEqual(response.json()['product']['id'], product.pk)

	def test_search_by_barcode_accepts_sku(self):
		product = Product.objects.create(
			name='SKU Chocolate',
			type='chocolate',
			sku='SKU-CH-1',
			quantity=Decimal('2'),
			purchase_price=Decimal('12.00'),
			selling_price=Decimal('20.00'),
		)

		response = self.client.get(reverse('sales:search_by_barcode'), {'barcode': product.sku})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['product']['id'], product.pk)

	def test_search_by_barcode_rejects_out_of_stock_product(self):
		product = Product.objects.create(
			name='Empty Gift',
			type='gift',
			sku='SKU-GF-0',
			barcode='000000000001',
			quantity=Decimal('0'),
			purchase_price=Decimal('10.00'),
			selling_price=Decimal('30.00'),
		)

		response = self.client.get(reverse('sales:search_by_barcode'), {'barcode': product.barcode})

		self.assertEqual(response.status_code, 400)
		self.assertFalse(response.json()['success'])
