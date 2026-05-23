from datetime import datetime, timedelta, time
from django.conf import settings
from django.db import models
from django.utils import timezone

class Supplier(models.Model):
	name = models.CharField(max_length=200)
	phone = models.CharField(max_length=20)
	email = models.EmailField(blank=True)
	address = models.TextField(blank=True)
	contact_person = models.CharField(max_length=100, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name

	class Meta:
		verbose_name = 'مورد'
		verbose_name_plural = 'الموردون'

class Product(models.Model):
	TYPE_CHOICES = [
		('flower', 'ورد طازج'),
		('chocolate', 'شوكولاته'),
		('gift', 'هدية جاهزة'),
	]
	UNIT_CHOICES = [
		('piece', 'قطعة'),
		('bundle', 'باقة'),
		('box', 'علبة'),
		('kg', 'كيلو'),
	]
	name = models.CharField(max_length=200)
	type = models.CharField(max_length=20, choices=TYPE_CHOICES)
	category = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True)
	sku = models.CharField(max_length=50, unique=True, blank=True)
	barcode = models.CharField(max_length=50, blank=True)
	quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=5)
	purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
	selling_price = models.DecimalField(max_digits=10, decimal_places=2)
	is_fresh = models.BooleanField(default=True)
	harvest_date = models.DateField(null=True, blank=True)
	shelf_life_hours = models.IntegerField(default=48, help_text='ساعات الصلاحية للورد')
	storage_temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='درجة حرارة التخزين المثالية')
	is_seasonal = models.BooleanField(default=False)
	image = models.ImageField(upload_to='products/', blank=True, null=True)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def save(self, *args, **kwargs):
		if not self.sku:
			prefix = 'FL' if self.type == 'flower' else 'CH' if self.type == 'chocolate' else 'GF'
			self.sku = f"{prefix}{timezone.now().strftime('%Y%m%d%H%M%S')}"
		super().save(*args, **kwargs)

	@property
	def is_expiring_soon(self):
		if self.type != 'flower' or not self.harvest_date:
			return False

		harvest_datetime = datetime.combine(self.harvest_date, time.min)
		if timezone.is_naive(harvest_datetime):
			harvest_datetime = timezone.make_aware(harvest_datetime, timezone.get_current_timezone())

		expiry_datetime = harvest_datetime + timedelta(hours=self.shelf_life_hours)
		return (expiry_datetime - timezone.now()) < timedelta(hours=8)

	@property
	def profit_margin(self):
		if self.purchase_price > 0:
			return ((self.selling_price - self.purchase_price) / self.purchase_price) * 100
		return 0

	def __str__(self):
		return f"{self.name} ({self.get_type_display()})"

	class Meta:
		verbose_name = 'منتج'
		verbose_name_plural = 'المنتجات'

class StockMovement(models.Model):
	MOVEMENT_TYPES = [
		('in', 'داخل (شراء)'),
		('out', 'خارج (بيع)'),
		('adjust', 'تعديل يدوي'),
		('waste', 'تالف/منتهي'),
	]

	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	quantity = models.DecimalField(max_digits=10, decimal_places=2)
	movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
	notes = models.TextField(blank=True)
	reference = models.CharField(max_length=100, blank=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		previous_quantity = None
		previous_movement_type = None

		if self.pk:
			previous = StockMovement.objects.filter(pk=self.pk).only('quantity', 'movement_type').first()
			if previous:
				previous_quantity = previous.quantity
				previous_movement_type = previous.movement_type

		def movement_delta(movement_type, quantity):
			if movement_type == 'in':
				return quantity
			if movement_type in {'out', 'waste'}:
				return -quantity
			return quantity

		if previous_quantity is not None and previous_movement_type is not None:
			self.product.quantity -= movement_delta(previous_movement_type, previous_quantity)

		self.product.quantity += movement_delta(self.movement_type, self.quantity)
		self.product.save()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"
from django.db import models

# Create your models here.
