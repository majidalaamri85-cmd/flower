from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import role_required

from .forms import ProductForm, StockAdjustForm, SupplierForm
from .models import Product, StockMovement, Supplier


@login_required
def product_list(request):
	products = Product.objects.filter(is_active=True).select_related('category')

	product_type = request.GET.get('type')
	if product_type and product_type != 'all':
		products = products.filter(type=product_type)

	category = request.GET.get('category')
	if category:
		products = products.filter(category_id=category)

	search = request.GET.get('search')
	if search:
		products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(barcode__icontains=search))

	low_stock_alerts = products.filter(quantity__lte=F('min_stock'))
	expiring_alerts = products.filter(type='flower', harvest_date__isnull=False)

	paginator = Paginator(products.order_by('name'), 20)
	page_obj = paginator.get_page(request.GET.get('page'))

	return render(
		request,
		'inventory/product_list.html',
		{
			'products': page_obj,
			'low_stock_count': low_stock_alerts.count(),
			'expiring_count': expiring_alerts.count(),
			'search': search,
			'current_type': product_type,
		},
	)


@login_required
@role_required(['admin', 'manager'])
def product_create(request):
	form = ProductForm(request.POST or None, request.FILES or None)
	if request.method == 'POST' and form.is_valid():
		product = form.save()
		messages.success(request, f'تم إضافة المنتج {product.name} بنجاح')
		return redirect('inventory:product_list')
	return render(request, 'inventory/product_form.html', {'form': form, 'title': 'إضافة منتج جديد'})


@login_required
@role_required(['admin', 'manager'])
def product_edit(request, pk):
	product = get_object_or_404(Product, pk=pk)
	form = ProductForm(request.POST or None, request.FILES or None, instance=product)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, f'تم تعديل المنتج {product.name} بنجاح')
		return redirect('inventory:product_list')
	return render(request, 'inventory/product_form.html', {'form': form, 'title': 'تعديل منتج', 'product': product})


@login_required
@role_required(['admin'])
def product_delete(request, pk):
	product = get_object_or_404(Product, pk=pk)
	if request.method == 'POST':
		product.is_active = False
		product.save(update_fields=['is_active'])
		messages.success(request, f'تم حذف المنتج {product.name} بنجاح')
		return redirect('inventory:product_list')
	return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@login_required
@role_required(['admin', 'manager'])
def stock_adjust(request, pk):
	product = get_object_or_404(Product, pk=pk)
	form = StockAdjustForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		stock_movement = form.save(commit=False)
		stock_movement.product = product
		stock_movement.reference = f"MANUAL-{timezone.now().strftime('%Y%m%d%H%M%S')}"
		stock_movement.created_by = request.user
		stock_movement.save()
		messages.success(request, f'تم تعديل مخزون {product.name} بنجاح')
		return redirect('inventory:product_list')
	return render(request, 'inventory/stock_adjust.html', {'form': form, 'product': product})


@login_required
def stock_movements(request):
	movements = StockMovement.objects.select_related('product', 'created_by').order_by('-created_at')

	product_id = request.GET.get('product')
	if product_id:
		movements = movements.filter(product_id=product_id)

	movement_type = request.GET.get('type')
	if movement_type:
		movements = movements.filter(movement_type=movement_type)

	date_from = request.GET.get('date_from')
	if date_from:
		movements = movements.filter(created_at__date__gte=date_from)

	date_to = request.GET.get('date_to')
	if date_to:
		movements = movements.filter(created_at__date__lte=date_to)

	paginator = Paginator(movements, 50)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'inventory/stock_movements.html', {'movements': page_obj, 'products': Product.objects.filter(is_active=True)})


@login_required
def low_stock_alert(request):
	products = Product.objects.filter(is_active=True, quantity__lte=F('min_stock')).order_by('quantity')
	return render(request, 'inventory/low_stock.html', {'products': products})


@login_required
def expiring_flowers(request):
	products = Product.objects.filter(type='flower', is_active=True, harvest_date__isnull=False)

	expiring_list = []
	now = timezone.now()
	for product in products:
		harvest_dt = datetime.combine(product.harvest_date, time.min)
		harvest_dt = timezone.make_aware(harvest_dt, timezone.get_current_timezone())
		expiry_dt = harvest_dt + timedelta(hours=product.shelf_life_hours)
		hours_left = (expiry_dt - now).total_seconds() / 3600
		if hours_left <= 24:
			expiring_list.append({'product': product, 'hours_left': hours_left})

	expiring_list.sort(key=lambda item: item['hours_left'])
	return render(request, 'inventory/expiring_flowers.html', {'expiring_flowers': expiring_list})


@login_required
@role_required(['admin', 'manager'])
def supplier_list(request):
	suppliers = Supplier.objects.all().order_by('name')
	search = request.GET.get('search')
	if search:
		suppliers = suppliers.filter(Q(name__icontains=search) | Q(phone__icontains=search) | Q(contact_person__icontains=search))
	return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers, 'search': search})


@login_required
@role_required(['admin', 'manager'])
def supplier_create(request):
	form = SupplierForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		supplier = form.save()
		messages.success(request, f'تم إضافة المورد {supplier.name} بنجاح')
		return redirect('inventory:supplier_list')
	return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'إضافة مورد'})
