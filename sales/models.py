import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

class Customer(models.Model):
	name = models.CharField(max_length=200)
	phone = models.CharField(max_length=20)
	email = models.EmailField(blank=True)
	address = models.TextField(blank=True)
	favorite_flower = models.CharField(max_length=100, blank=True)
	favorite_chocolate = models.CharField(max_length=100, blank=True)
	total_purchases = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	last_purchase_date = models.DateTimeField(null=True, blank=True)
	is_vip = models.BooleanField(default=False)
	birth_date = models.DateField(null=True, blank=True)
	anniversary_date = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.name} - {self.phone}"

	class Meta:
		verbose_name = 'عميل'
		verbose_name_plural = 'العملاء'

class Sale(models.Model):
	PAYMENT_METHODS = [
		('cash', 'نقدي'),
		('card', 'بطاقة'),
		('bank_transfer', 'تحويل بنكي'),
		('mada', 'مدى'),
	]

	invoice_number = models.CharField(max_length=50, unique=True)
	customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
	employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	subtotal = models.DecimalField(max_digits=10, decimal_places=2)
	discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	total = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
	paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
	change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	notes = models.TextField(blank=True)
	is_delivery = models.BooleanField(default=False)
	delivery_address = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	@staticmethod
	def _generate_invoice_number():
		today = timezone.now().strftime('%Y%m%d')
		last_invoice = Sale.objects.filter(invoice_number__startswith=f'INV-{today}').order_by('-invoice_number').first()

		if last_invoice:
			last_num = int(last_invoice.invoice_number.split('-')[-1])
			next_num = last_num + 1
		else:
			next_num = 1

		return f'INV-{today}-{next_num:04d}'

	def save(self, *args, **kwargs):
		if not self.invoice_number:
			with transaction.atomic():
				self.invoice_number = self._generate_invoice_number()

		self.change_amount = self.paid_amount - self.total
		super().save(*args, **kwargs)

	def __str__(self):
		return f"فاتورة {self.invoice_number} - {self.total} ر.ع"

	class Meta:
		verbose_name = 'بيعة'
		verbose_name_plural = 'المبيعات'
		ordering = ['-created_at']

class SaleItem(models.Model):
	sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
	quantity = models.DecimalField(max_digits=10, decimal_places=2)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)
	total = models.DecimalField(max_digits=10, decimal_places=2)

	def save(self, *args, **kwargs):
		self.total = self.quantity * self.unit_price
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.product.name} x {self.quantity}"

class BundleOffer(models.Model):
	name = models.CharField(max_length=200)
	flower_product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='flower_bundles', limit_choices_to={'type': 'flower'})
	chocolate_product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='chocolate_bundles', limit_choices_to={'type': 'chocolate'})
	flower_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
	chocolate_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
	bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
	regular_price = models.DecimalField(max_digits=10, decimal_places=2)
	start_date = models.DateField()
	end_date = models.DateField()
	is_active = models.BooleanField(default=True)

	@property
	def savings(self):
		return self.regular_price - self.bundle_price

	def __str__(self):
		return f"{self.name} - توفير {self.savings} ر.ع"


class OfflineSaleQueue(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	sale_data = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)
	synced_at = models.DateTimeField(null=True, blank=True)
	is_synced = models.BooleanField(default=False)
	sync_attempts = models.IntegerField(default=0)

	class Meta:
		verbose_name = 'مبيعات دون اتصال'
		verbose_name_plural = 'مبيعات دون اتصال'
		ordering = ['created_at']
