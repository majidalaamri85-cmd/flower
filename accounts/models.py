from django.conf import settings
from django.db import models
from django.utils import timezone

class ExpenseCategory(models.Model):
	CATEGORY_TYPES = [
		('operational', 'تشغيلية'),
		('maintenance', 'صيانة'),
		('supplies', 'لوازم'),
		('rent', 'إيجار'),
		('salaries', 'رواتب'),
		('utilities', 'فواتير خدمات'),
		('marketing', 'تسويق'),
		('transport', 'نقل وتوصيل'),
		('other', 'أخرى'),
	]

	name = models.CharField(max_length=100, unique=True)
	category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='other')
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	icon = models.CharField(max_length=50, default='fas fa-receipt', help_text='أيقونة Font Awesome')
	color = models.CharField(max_length=20, default='primary', help_text='لون Bootstrap')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name

	class Meta:
		verbose_name = 'فئة مصروف'
		verbose_name_plural = 'فئات المصروفات'
		ordering = ['name']

class Expense(models.Model):
	PAYMENT_METHODS = [
		('cash', 'نقدي'),
		('bank', 'تحويل بنكي'),
		('card', 'بطاقة'),
	]

	category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	description = models.TextField()
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
	receipt = models.FileField(upload_to='expenses/%Y/%m/', blank=True, null=True)
	receipt_number = models.CharField(max_length=100, blank=True, help_text='رقم الإيصال أو الفاتورة')
	expense_date = models.DateField(default=timezone.localdate)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	notes = models.TextField(blank=True)

	def __str__(self):
		return f"{self.category.name} - {self.amount} ريال - {self.expense_date}"

	class Meta:
		verbose_name = 'مصروف'
		verbose_name_plural = 'المصروفات'
		ordering = ['-expense_date', '-created_at']
