import json
import os
from decimal import Decimal, InvalidOperation
from io import BytesIO
from datetime import timedelta

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.models import ShopSettings
from inventory.models import Product, StockMovement

from .models import BundleOffer, Customer, Sale, SaleItem

from django.forms import modelform_factory

CustomerForm = modelform_factory(Customer, fields=['name', 'phone', 'email', 'address'])
BundleOfferForm = modelform_factory(BundleOffer, fields=['name', 'flower_product', 'chocolate_product', 'flower_quantity', 'chocolate_quantity', 'bundle_price', 'regular_price', 'start_date', 'end_date', 'is_active'])


_PDF_FONT_REGISTERED = False
_PDF_FONT_REGULAR = 'Helvetica'
_PDF_FONT_BOLD = 'Helvetica-Bold'


def _first_existing_path(paths):
	for path in paths:
		if path and os.path.exists(path):
			return path
	return None


def _register_pdf_fonts():
	global _PDF_FONT_REGISTERED, _PDF_FONT_REGULAR, _PDF_FONT_BOLD
	if _PDF_FONT_REGISTERED:
		return

	regular_path = _first_existing_path([
		os.environ.get('INVOICE_FONT_PATH'),
		os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf'),
		'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
		'/usr/local/share/fonts/DejaVuSans.ttf',
		r'C:\Windows\Fonts\tahoma.ttf',
		r'C:\Windows\Fonts\arial.ttf',
	])
	bold_path = _first_existing_path([
		os.environ.get('INVOICE_BOLD_FONT_PATH'),
		os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf'),
		'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
		'/usr/local/share/fonts/DejaVuSans-Bold.ttf',
		r'C:\Windows\Fonts\tahomabd.ttf',
		r'C:\Windows\Fonts\arialbd.ttf',
		regular_path,
	])

	if regular_path:
		pdfmetrics.registerFont(TTFont('InvoiceArabic', regular_path))
		_PDF_FONT_REGULAR = 'InvoiceArabic'
	if bold_path:
		pdfmetrics.registerFont(TTFont('InvoiceArabicBold', bold_path))
		_PDF_FONT_BOLD = 'InvoiceArabicBold'
	_PDF_FONT_REGISTERED = True


def _pdf_text(value):
	text = '' if value is None else str(value)
	if any('\u0600' <= char <= '\u06ff' for char in text):
		return get_display(arabic_reshaper.reshape(text))
	return text


def _pdf_paragraph(value, style):
	return Paragraph(_pdf_text(value), style)


def _cart(request):
	return request.session.get('cart', {})


def _json_body(request):
	try:
		return json.loads(request.body or '{}')
	except json.JSONDecodeError:
		return None


def _positive_decimal(value, default=None):
	try:
		amount = Decimal(str(value if value not in {None, ''} else default))
	except (InvalidOperation, TypeError):
		return None
	return amount if amount > 0 else None


def _money_decimal(value, default='0'):
	try:
		amount = Decimal(str(value if value not in {None, ''} else default))
	except (InvalidOperation, TypeError):
		return None
	return amount if amount >= 0 else None


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
@ensure_csrf_cookie
def pos_offline(request):
	return render(request, 'sales/pos_offline.html')


@login_required
def search_product(request):
	query = request.GET.get('q', '')
	product_type = request.GET.get('type', '')
	products = Product.objects.filter(is_active=True, quantity__gt=0)
	if query:
		products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query))
	if product_type and product_type != 'all':
		products = products.filter(type=product_type)
	return render(request, 'sales/partials/product_list.html', {'products': products.order_by('quantity')[:20]})


@login_required
def search_by_barcode(request):
	barcode = request.GET.get('barcode', '').strip()
	if not barcode:
		return JsonResponse({'success': False, 'error': 'الباركود مطلوب'}, status=400)

	product = (
		Product.objects
		.filter(Q(barcode=barcode) | Q(sku=barcode), is_active=True)
		.first()
	)
	if not product:
		return JsonResponse({'success': False, 'error': 'المنتج غير موجود'}, status=404)
	if product.quantity <= 0:
		return JsonResponse({'success': False, 'error': 'المنتج غير متوفر في المخزون'}, status=400)

	return JsonResponse({
		'success': True,
		'product': {
			'id': product.pk,
			'name': product.name,
			'sku': product.sku,
			'barcode': product.barcode,
			'quantity': str(product.quantity),
			'selling_price': str(product.selling_price),
		},
	})


@login_required
def add_to_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = _json_body(request)
	if data is None:
		return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
	product = get_object_or_404(Product, pk=data.get('product_id'), is_active=True)
	quantity = _positive_decimal(data.get('quantity'), default='1')
	if quantity is None:
		return JsonResponse({'error': 'Quantity must be greater than zero'}, status=400)
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
def remove_from_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = _json_body(request)
	if data is None:
		return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
	cart = request.session.get('cart', {})
	cart.pop(str(data.get('product_id')), None)
	request.session['cart'] = cart
	return JsonResponse({'success': True})


@login_required
def update_cart(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Invalid request'}, status=400)
	data = _json_body(request)
	if data is None:
		return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
	product = get_object_or_404(Product, pk=data.get('product_id'), is_active=True)
	try:
		quantity = Decimal(str(data.get('quantity', '0')))
	except (InvalidOperation, TypeError):
		return JsonResponse({'error': 'Invalid quantity'}, status=400)
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
		quantity = _positive_decimal(item.get('quantity'))
		price = _money_decimal(item.get('price'))
		if quantity is None or price is None:
			messages.error(request, 'تحتوي السلة على منتج بكمية أو سعر غير صالح')
			return redirect('sales:pos')
		subtotal += quantity * price

	discount = _money_decimal(request.POST.get('discount'), default='0')
	tax = _money_decimal(request.POST.get('tax'), default='0')
	if discount is None or tax is None:
		messages.error(request, 'تأكد من إدخال مبالغ صحيحة غير سالبة')
		return redirect('sales:pos')
	total = subtotal - discount + tax
	if total < 0:
		messages.error(request, 'إجمالي الفاتورة لا يمكن أن يكون سالباً')
		return redirect('sales:pos')
	paid_amount = _money_decimal(request.POST.get('paid_amount'), default='0')
	if paid_amount is None:
		messages.error(request, 'تأكد من إدخال مبلغ مدفوع صحيح')
		return redirect('sales:pos')
	if paid_amount < total:
		messages.error(request, 'المبلغ المدفوع أقل من إجمالي الفاتورة')
		return redirect('sales:pos')

	prepared_items = []
	for product_id, item in cart.items():
		product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, is_active=True)
		quantity = _positive_decimal(item.get('quantity'))
		unit_price = _money_decimal(item.get('price'))
		if quantity is None or unit_price is None:
			messages.error(request, 'تحتوي السلة على منتج بكمية أو سعر غير صالح')
			return redirect('sales:pos')
		if quantity > product.quantity:
			messages.error(request, f'الكمية المتوفرة من {product.name}: {product.quantity}')
			return redirect('sales:pos')
		prepared_items.append((product, quantity, unit_price))

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

	for product, quantity, unit_price in prepared_items:
		SaleItem.objects.create(sale=sale, product=product, quantity=quantity, unit_price=unit_price, total=quantity * unit_price)
		try:
			StockMovement.objects.create(
				product=product,
				quantity=quantity,
				movement_type='out',
				reference=f'INV-{sale.invoice_number}',
				notes=f'بيع - فاتورة {sale.invoice_number}',
				created_by=request.user,
			)
		except ValidationError:
			transaction.set_rollback(True)
			messages.error(request, f'المخزون غير كاف للمنتج {product.name}')
			return redirect('sales:pos')

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
@transaction.atomic
def invoice_edit(request, invoice_number):
	sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('items__product'), invoice_number=invoice_number)
	customers = Customer.objects.order_by('name')
	if request.method == 'POST':
		old_total = sale.total
		old_customer = sale.customer
		try:
			discount = Decimal(request.POST.get('discount', '0') or '0')
			tax = Decimal(request.POST.get('tax', '0') or '0')
			paid_amount = Decimal(request.POST.get('paid_amount', '0') or '0')
		except InvalidOperation:
			messages.error(request, 'تأكد من إدخال أرقام صحيحة في المبالغ')
			return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)

		subtotal = Decimal('0')
		for item in sale.items.select_related('product'):
			try:
				new_quantity = Decimal(request.POST.get(f'item_{item.pk}_quantity', item.quantity) or '0')
				new_unit_price = Decimal(request.POST.get(f'item_{item.pk}_unit_price', item.unit_price) or '0')
			except InvalidOperation:
				messages.error(request, f'تأكد من كمية وسعر المنتج: {item.product.name}')
				return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)

			if new_quantity < 0 or new_unit_price < 0:
				messages.error(request, 'الكمية والسعر لا يمكن أن تكون سالبة')
				return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)

			stock_delta = item.quantity - new_quantity
			if stock_delta < 0 and item.product.quantity < abs(stock_delta):
				messages.error(request, f'المخزون غير كاف لزيادة كمية {item.product.name}')
				return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)

			if stock_delta:
				StockMovement.objects.create(
					product=item.product,
					quantity=stock_delta,
					movement_type='adjust',
					reference=f'EDIT-{sale.invoice_number}',
					notes=f'تعديل فاتورة {sale.invoice_number}: فرق الكمية {stock_delta}',
					created_by=request.user,
				)

			if new_quantity == 0:
				item.delete()
				continue

			item.quantity = new_quantity
			item.unit_price = new_unit_price
			item.total = new_quantity * new_unit_price
			item.save(update_fields=['quantity', 'unit_price', 'total'])
			subtotal += item.total

		total = subtotal - discount + tax
		if total < 0:
			messages.error(request, 'إجمالي الفاتورة لا يمكن أن يكون سالباً')
			return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)
		if paid_amount < total:
			messages.error(request, 'المبلغ المدفوع أقل من إجمالي الفاتورة')
			return redirect('sales:invoice_edit', invoice_number=sale.invoice_number)

		customer_id = request.POST.get('customer_id')
		sale.customer = Customer.objects.filter(pk=customer_id).first() if customer_id else None
		sale.subtotal = subtotal
		sale.discount = discount
		sale.tax = tax
		sale.total = total
		sale.paid_amount = paid_amount
		sale.payment_method = request.POST.get('payment_method', sale.payment_method)
		sale.notes = request.POST.get('notes', '')
		sale.is_delivery = request.POST.get('is_delivery') == 'on'
		sale.delivery_address = request.POST.get('delivery_address', '')
		sale.save()

		if old_customer:
			old_customer.total_purchases = max(old_customer.total_purchases - old_total, Decimal('0'))
			old_customer.save(update_fields=['total_purchases'])
		if sale.customer:
			sale.customer.total_purchases += sale.total
			sale.customer.last_purchase_date = timezone.now()
			sale.customer.save(update_fields=['total_purchases', 'last_purchase_date'])

		messages.success(request, f'تم تعديل الفاتورة {sale.invoice_number} بنجاح')
		return redirect('sales:invoice_detail', invoice_number=sale.invoice_number)

	return render(request, 'sales/invoice_form.html', {'sale': sale, 'customers': customers})


@login_required
@require_POST
@transaction.atomic
def invoice_delete(request, invoice_number):
	sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), invoice_number=invoice_number)
	for item in sale.items.select_related('product'):
		product = item.product
		StockMovement.objects.create(
			product=product,
			quantity=item.quantity,
			movement_type='adjust',
			reference=f'DELETE-{sale.invoice_number}',
			notes=f'استرجاع {item.quantity} للمخزون بعد حذف الفاتورة {sale.invoice_number}',
			created_by=request.user,
		)

	if sale.customer:
		sale.customer.total_purchases = max(sale.customer.total_purchases - sale.total, Decimal('0'))
		sale.customer.save(update_fields=['total_purchases'])

	sale.delete()
	messages.success(request, f'تم حذف الفاتورة {invoice_number} واسترجاع الكميات للمخزون')
	return redirect('sales:invoice_list')


@login_required
def invoice_pdf(request, invoice_number):
	sale = get_object_or_404(Sale.objects.prefetch_related('items__product').select_related('customer', 'employee'), invoice_number=invoice_number)
	_register_pdf_fonts()
	shop = ShopSettings.objects.first()
	currency_symbol = shop.currency_symbol if shop and shop.currency_symbol else 'ر.ع'
	buffer = BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
	styles = getSampleStyleSheet()
	title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontName=_PDF_FONT_BOLD, alignment=2, fontSize=18, leading=24, textColor=colors.HexColor('#243042'))
	normal_style = ParagraphStyle('InvoiceNormal', parent=styles['Normal'], fontName=_PDF_FONT_REGULAR, alignment=2, fontSize=10, leading=15)
	bold_style = ParagraphStyle('InvoiceBold', parent=normal_style, fontName=_PDF_FONT_BOLD)
	footer_style = ParagraphStyle('InvoiceFooter', parent=normal_style, alignment=1, fontName=_PDF_FONT_BOLD, textColor=colors.HexColor('#4f8a5b'))
	elements = [_pdf_paragraph(f'فاتورة رقم {sale.invoice_number}', title_style), Spacer(1, 12)]

	if shop:
		shop_data = [
			[_pdf_paragraph(shop.shop_name, bold_style), _pdf_paragraph('اسم المحل', normal_style)],
			[_pdf_paragraph(shop.phone, normal_style), _pdf_paragraph('الهاتف', normal_style)],
			[_pdf_paragraph(shop.email, normal_style), _pdf_paragraph('البريد', normal_style)],
			[_pdf_paragraph(shop.address, normal_style), _pdf_paragraph('العنوان', normal_style)],
		]
		shop_table = Table(shop_data, colWidths=[11 * cm, 4 * cm], hAlign='RIGHT')
		shop_table.setStyle(TableStyle([
			('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fffaf2')),
			('BOX', (0, 0), (-1, -1), .6, colors.HexColor('#eadde2')),
			('INNERGRID', (0, 0), (-1, -1), .4, colors.HexColor('#eadde2')),
			('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
			('RIGHTPADDING', (0, 0), (-1, -1), 8),
			('LEFTPADDING', (0, 0), (-1, -1), 8),
		]))
		elements.append(shop_table)
		elements.append(Spacer(1, 12))

	customer_name = sale.customer.name if sale.customer else 'عميل نقدي'
	employee_name = sale.employee.get_full_name() if sale.employee and sale.employee.get_full_name() else (sale.employee.username if sale.employee else '-')
	meta_data = [
		[_pdf_paragraph(customer_name, normal_style), _pdf_paragraph('العميل', bold_style)],
		[_pdf_paragraph(f'{sale.created_at:%Y-%m-%d %H:%M}', normal_style), _pdf_paragraph('التاريخ', bold_style)],
		[_pdf_paragraph(employee_name, normal_style), _pdf_paragraph('الموظف', bold_style)],
	]
	meta_table = Table(meta_data, colWidths=[11 * cm, 4 * cm], hAlign='RIGHT')
	meta_table.setStyle(TableStyle([
		('BOX', (0, 0), (-1, -1), .6, colors.HexColor('#eadde2')),
		('INNERGRID', (0, 0), (-1, -1), .4, colors.HexColor('#eadde2')),
		('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
		('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#eff8ef')),
		('RIGHTPADDING', (0, 0), (-1, -1), 8),
		('LEFTPADDING', (0, 0), (-1, -1), 8),
	]))
	elements.append(meta_table)
	elements.append(Spacer(1, 12))

	table_data = [[
		_pdf_paragraph('الإجمالي', bold_style),
		_pdf_paragraph('سعر الوحدة', bold_style),
		_pdf_paragraph('الكمية', bold_style),
		_pdf_paragraph('المنتج', bold_style),
	]]
	for item in sale.items.all():
		table_data.append([
			_pdf_paragraph(f'{item.total} {currency_symbol}', normal_style),
			_pdf_paragraph(f'{item.unit_price} {currency_symbol}', normal_style),
			_pdf_paragraph(item.quantity, normal_style),
			_pdf_paragraph(item.product.name, normal_style),
		])
	table_data.extend([
		[_pdf_paragraph(f'{sale.subtotal} {currency_symbol}', normal_style), _pdf_paragraph('المجموع الفرعي', bold_style), '', ''],
		[_pdf_paragraph(f'{sale.discount} {currency_symbol}', normal_style), _pdf_paragraph('الخصم', bold_style), '', ''],
		[_pdf_paragraph(f'{sale.tax} {currency_symbol}', normal_style), _pdf_paragraph('الضريبة', bold_style), '', ''],
		[_pdf_paragraph(f'{sale.total} {currency_symbol}', bold_style), _pdf_paragraph('الإجمالي', bold_style), '', ''],
		[_pdf_paragraph(f'{sale.paid_amount} {currency_symbol}', normal_style), _pdf_paragraph('المدفوع', bold_style), '', ''],
		[_pdf_paragraph(f'{sale.change_amount} {currency_symbol}', normal_style), _pdf_paragraph('الباقي', bold_style), '', ''],
	])
	table = Table(table_data, colWidths=[3.5 * cm, 3.5 * cm, 2.5 * cm, 6.5 * cm], hAlign='RIGHT')
	table.setStyle(TableStyle([
		('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f8a5b')),
		('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
		('BACKGROUND', (0, -3), (1, -3), colors.HexColor('#fff1f5')),
		('GRID', (0, 0), (-1, -1), .5, colors.HexColor('#eadde2')),
		('ALIGN', (0, 0), (-1, -1), 'CENTER'),
		('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
		('FONTNAME', (0, 0), (-1, -1), _PDF_FONT_REGULAR),
		('FONTNAME', (0, 0), (-1, 0), _PDF_FONT_BOLD),
		('RIGHTPADDING', (0, 0), (-1, -1), 8),
		('LEFTPADDING', (0, 0), (-1, -1), 8),
	]))
	elements.append(table)
	elements.append(Spacer(1, 20))
	elements.append(_pdf_paragraph('شكراً لتسوقكم معنا', footer_style))
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
