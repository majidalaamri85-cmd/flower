from django.db import models


class ShopSettings(models.Model):
    shop_name = models.CharField(max_length=200, default='ROOTS FLOWERS')
    shop_logo = models.ImageField(upload_to='logo/', blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    tax_number = models.CharField(max_length=50, blank=True)
    currency_symbol = models.CharField(max_length=10, default='ر.ع')

    def __str__(self):
        return self.shop_name

    class Meta:
        verbose_name = 'إعدادات المحل'
        verbose_name_plural = 'إعدادات المحل'


class Category(models.Model):
    TYPE_CHOICES = [
        ('flower', 'ورد'),
        ('chocolate', 'شوكولاته'),
        ('gift', 'هدايا'),
        ('accessory', 'إكسسوارات'),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    class Meta:
        verbose_name_plural = 'التصنيفات'
