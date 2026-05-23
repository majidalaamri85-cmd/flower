from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Expense
from inventory.models import Product
from sales.models import Sale

from .models import ShopSettings


def is_admin(user):
	return user.is_staff or user.is_superuser


@login_required
def dashboard(request):
	today = timezone.localdate()
	start_of_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))
	start_of_month = timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))

	today_sales = Sale.objects.filter(created_at__gte=start_of_today)
	month_sales = Sale.objects.filter(created_at__gte=start_of_month)
	products = Product.objects.filter(is_active=True)

	context = {
		'today_total': today_sales.aggregate(total=Sum('total'))['total'] or 0,
		'today_count': today_sales.count(),
		'month_total': month_sales.aggregate(total=Sum('total'))['total'] or 0,
		'low_stock_count': products.filter(quantity__lte=F('min_stock')).count(),
		'expiring_flowers_count': products.filter(type='flower', harvest_date__isnull=False).count(),
		'today_expenses': Expense.objects.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or 0,
		'recent_sales': Sale.objects.select_related('customer').order_by('-created_at')[:10],
		'low_stock_list': products.filter(quantity__lte=F('min_stock'))[:10],
	}
	context['today_profit'] = context['today_total'] - context['today_expenses']
	return render(request, 'core/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def shop_settings(request):
	shop_settings_obj, _ = ShopSettings.objects.get_or_create(pk=1)

	if request.method == 'POST':
		shop_settings_obj.shop_name = request.POST.get('shop_name', shop_settings_obj.shop_name)
		shop_settings_obj.phone = request.POST.get('phone', shop_settings_obj.phone)
		shop_settings_obj.email = request.POST.get('email', shop_settings_obj.email)
		shop_settings_obj.address = request.POST.get('address', shop_settings_obj.address)
		shop_settings_obj.tax_number = request.POST.get('tax_number', shop_settings_obj.tax_number)
		shop_settings_obj.currency_symbol = request.POST.get('currency_symbol', shop_settings_obj.currency_symbol)
		if request.FILES.get('shop_logo'):
			shop_settings_obj.shop_logo = request.FILES['shop_logo']
		shop_settings_obj.save()
		messages.success(request, 'تم حفظ إعدادات المحل بنجاح')
		return redirect('core:settings')

	return render(request, 'core/settings.html', {'settings': shop_settings_obj})
