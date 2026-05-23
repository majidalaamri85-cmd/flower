import json
from decimal import Decimal
from io import BytesIO
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.models import ShopSettings
from inventory.models import Product, StockMovement

from .models import BundleOffer, Customer, Sale, SaleItem

from django.forms import modelform_factory

CustomerForm = modelform_factory(Customer, fields=['name', 'phone', 'email', 'address'])
BundleOfferForm = modelform_factory(BundleOffer, fields=['name', 'flower_product', 'chocolate_product', 'flower_quantity', 'chocolate_quantity', 'bundle_price', 'regular_price', 'start_date', 'end_date', 'is_active'])


def _cart(request):
	return request.session.get('cart', {})


def _cart_items(request):
	cart = _cart(request)
	items = []
	total = Decimal('0')
	for product_id, item in cart.items():
		product = Product.objects.filter(pk=product_id).first()
		if not product:
			continue
		quantity = Decimal(str(item['quantity']))
		price = Decimal(str(item['price']))
		line_total = quantity * price
		total += line_total
		items.append({
			'id': product_id,
			'name': product.name,
			'quantity': quantity,
			'price': price,
			'total': line_total,
			'image_url': product.image.url if product.image else None,
		})
	return items, total


@login_required
def pos(request):
	items, total = _cart_items(request)
	active_bundles = BundleOffer.objects.filter(is_active=True, start_date__lte=timezone.localdate(), end_date__gte=timezone.localdate())
	customers = Customer.objects.order_by('name')
	return render(request, 'sales/pos.html', {
		'cart_items': items,
		'cart_total': total,
		'active_bundles': active_bundles,
		'customers': customers,
	})


@login_required
def pos_offline(request):
	return render(request, 'sales/pos_offline.html')


@login_required
def search_product(request):
	query = request.GET.get('q', '')
	product_type = request.GET.get('type', '')
	products = Product.objects.filter(is_active=True, quantity__gt=0)
	if query:
		products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
	if product_type and product_type != 'all':
		products = products.filter(type=product_type)
	return render(request, 'sales/partials/product_list.html', {'products': products.order_by('quantity')[:20]})


@login_required
@csrf_exempt
def add_to_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = json.loads(request.body or '{}')
	product = get_object_or_404(Product, pk=data.get('product_id'))
	quantity = Decimal(str(data.get('quantity', '1')))
	if quantity > product.quantity:
		return JsonResponse({'error': f'الكمية المتوفرة: {product.quantity}'}, status=400)

	cart = request.session.get('cart', {})
	product_id = str(product.pk)
	if product_id in cart:
		new_quantity = Decimal(str(cart[product_id]['quantity'])) + quantity
		if new_quantity > product.quantity:
			return JsonResponse({'error': f'لا يمكن إضافة أكثر من {product.quantity}'}, status=400)
		cart[product_id]['quantity'] = str(new_quantity)
	else:
		cart[product_id] = {'name': product.name, 'quantity': str(quantity), 'price': str(product.selling_price), 'type': product.type}
	request.session['cart'] = cart
	return JsonResponse({'success': True, 'cart_count': len(cart)})


@login_required
@csrf_exempt
def remove_from_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = json.loads(request.body or '{}')
	cart = request.session.get('cart', {})
	cart.pop(str(data.get('product_id')), None)
	request.session['cart'] = cart
	return JsonResponse({'success': True})


@login_required
@csrf_exempt
def update_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = json.loads(request.body or '{}')
	product = get_object_or_404(Product, pk=data.get('product_id'))
	quantity = Decimal(str(data.get('quantity', '0')))
	cart = request.session.get('cart', {})
	product_id = str(product.pk)
	if quantity <= 0:
		cart.pop(product_id, None)
	else:
		if quantity > product.quantity:
			return JsonResponse({'error': f'الكمية المتوفرة: {product.quantity}'}, status=400)
		cart[product_id] = {'name': product.name, 'quantity': str(quantity), 'price': str(product.selling_price), 'type': product.type}
	request.session['cart'] = cart
	return JsonResponse({'success': True})


@login_required
@transaction.atomic
def checkout(request):
	if request.method != 'POST':
		return redirect('sales:pos')

	cart = request.session.get('cart', {})
	if not cart:
		messages.error(request, 'السلة فارغة')
		return redirect('sales:pos')

	subtotal = Decimal('0')
	for item in cart.values():
		subtotal += Decimal(str(item['quantity'])) * Decimal(str(item['price']))

	discount = Decimal(request.POST.get('discount', '0'))
	tax = Decimal(request.POST.get('tax', '0'))
	total = subtotal - discount + tax
	paid_amount = Decimal(request.POST.get('paid_amount', '0'))
	if paid_amount < total:
		messages.error(request, 'المبلغ المدفوع أقل من إجمالي الفاتورة')
		return redirect('sales:pos')

	customer = None
	customer_id = request.POST.get('customer_id')
	if customer_id:
		customer = get_object_or_404(Customer, pk=customer_id)
	elif request.POST.get('customer_name'):
		customer = Customer.objects.create(
			name=request.POST.get('customer_name', ''),
			phone=request.POST.get('customer_phone', ''),
			email=request.POST.get('customer_email', ''),
		)

	sale = Sale.objects.create(
		customer=customer,
		employee=request.user,
		subtotal=subtotal,
		discount=discount,
		tax=tax,
		total=total,
		payment_method=request.POST.get('payment_method', 'cash'),
		paid_amount=paid_amount,
		notes=request.POST.get('notes', ''),
		is_delivery=request.POST.get('is_delivery') == 'on',
		delivery_address=request.POST.get('delivery_address', ''),
	)

	for product_id, item in cart.items():
		product = get_object_or_404(Product, pk=product_id)
		quantity = Decimal(str(item['quantity']))
		unit_price = Decimal(str(item['price']))
		SaleItem.objects.create(sale=sale, product=product, quantity=quantity, unit_price=unit_price, total=quantity * unit_price)
		StockMovement.objects.create(
			product=product,
			quantity=quantity,
			movement_type='out',
			reference=f'INV-{sale.invoice_number}',
			notes=f'بيع - فاتورة {sale.invoice_number}',
			created_by=request.user,
		)

	if customer:
		customer.total_purchases += total
		customer.last_purchase_date = timezone.now()
		customer.save()

	request.session['cart'] = {}
	messages.success(request, f'تمت عملية البيع بنجاح - رقم الفاتورة: {sale.invoice_number}')
	return redirect('sales:invoice_detail', invoice_number=sale.invoice_number)


@login_required
def invoice_list(request):
	invoices = Sale.objects.select_related('customer', 'employee').order_by('-created_at')
	date_filter = request.GET.get('date')
	if date_filter == 'today':
		invoices = invoices.filter(created_at__date=timezone.localdate())
	elif date_filter == 'week':
		invoices = invoices.filter(created_at__gte=timezone.now() - timedelta(days=7))
	elif date_filter == 'month':
		invoices = invoices.filter(created_at__gte=timezone.now() - timedelta(days=30))
	return render(request, 'sales/invoice_list.html', {'invoices': invoices})


@login_required
def invoice_detail(request, invoice_number):
	sale = get_object_or_404(Sale.objects.select_related('customer', 'employee').prefetch_related('items__product'), invoice_number=invoice_number)
	return render(request, 'sales/invoice_detail.html', {'sale': sale})


@login_required
def invoice_pdf(request, invoice_number):
	sale = get_object_or_404(Sale.objects.prefetch_related('items__product').select_related('customer', 'employee'), invoice_number=invoice_number)
	buffer = BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
	styles = getSampleStyleSheet()
	elements = [Paragraph(f'فاتورة رقم {sale.invoice_number}', styles['Heading1']), Spacer(1, 12)]

	shop = ShopSettings.objects.first()
	if shop:
		elements.append(Paragraph(f'<b>{shop.shop_name}</b><br/>هاتف: {shop.phone}<br/>البريد: {shop.email}<br/>العنوان: {shop.address}', styles['Normal']))
		elements.append(Spacer(1, 12))

	customer_name = sale.customer.name if sale.customer else 'عميل نقدي'
	employee_name = sale.employee.get_full_name() if sale.employee and sale.employee.get_full_name() else (sale.employee.username if sale.employee else '-')
	elements.append(Paragraph(f'العميل: {customer_name}<br/>التاريخ: {sale.created_at:%Y-%m-%d %H:%M}<br/>الموظف: {employee_name}', styles['Normal']))
	elements.append(Spacer(1, 12))

	table_data = [['المنتج', 'الكمية', 'سعر الوحدة', 'الإجمالي']]
	for item in sale.items.all():
		table_data.append([item.product.name, str(item.quantity), f'{item.unit_price} ريال', f'{item.total} ريال'])
	table_data.extend([
		['', '', 'المجموع الفرعي', f'{sale.subtotal} ريال'],
		['', '', 'الخصم', f'{sale.discount} ريال'],
		['', '', 'الضريبة', f'{sale.tax} ريال'],
		['', '', 'الإجمالي', f'{sale.total} ريال'],
		['', '', 'المدفوع', f'{sale.paid_amount} ريال'],
		['', '', 'الباقي', f'{sale.change_amount} ريال'],
	])
	table = Table(table_data, colWidths=[6 * cm, 3 * cm, 4 * cm, 4 * cm])
	table.setStyle(TableStyle([
		('BACKGROUND', (0, 0), (-1, 0), colors.grey),
		('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
		('GRID', (0, 0), (-1, -1), 1, colors.black),
		('ALIGN', (0, 0), (-1, -1), 'CENTER'),
		('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
	]))
	elements.append(table)
	elements.append(Spacer(1, 20))
	elements.append(Paragraph('شكراً لتسوقكم معنا', styles['Italic']))
	doc.build(elements)
	buffer.seek(0)
	response = HttpResponse(buffer, content_type='application/pdf')
	response['Content-Disposition'] = f'attachment; filename="invoice_{sale.invoice_number}.pdf"'
	return response


@login_required
def customer_list(request):
	customers = Customer.objects.order_by('-created_at')
	return render(request, 'core/list.html', {'title': 'العملاء', 'items': customers, 'columns': ['name', 'phone', 'email']})


@login_required
def customer_create(request):
	form = CustomerForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'تمت إضافة العميل')
		return redirect('sales:customer_list')
	return render(request, 'sales/customer_form.html', {'form': form, 'title': 'إضافة عميل'})


@login_required
def bundle_list(request):
	bundles = BundleOffer.objects.select_related('flower_product', 'chocolate_product').order_by('-start_date')
	return render(request, 'core/list.html', {'title': 'العروض المجمعة', 'items': bundles, 'columns': ['name', 'bundle_price', 'regular_price']})


@login_required
def bundle_create(request):
	form = BundleOfferForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'تمت إضافة العرض')
		return redirect('sales:bundle_list')
	return render(request, 'sales/bundle_form.html', {'form': form, 'title': 'إضافة عرض مجمع'})
