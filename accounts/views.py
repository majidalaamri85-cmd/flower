from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db.models import Avg, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ExpenseCategoryForm, ExpenseForm
from .models import Expense, ExpenseCategory


@login_required
def expense_list(request):
	expenses = Expense.objects.select_related('category', 'created_by').order_by('-expense_date', '-created_at')

	category_id = request.GET.get('category')
	if category_id and category_id != 'all':
		expenses = expenses.filter(category_id=category_id)

	payment_method = request.GET.get('payment_method')
	if payment_method:
		expenses = expenses.filter(payment_method=payment_method)

	date_from = request.GET.get('date_from')
	if date_from:
		expenses = expenses.filter(expense_date__gte=date_from)

	date_to = request.GET.get('date_to')
	if date_to:
		expenses = expenses.filter(expense_date__lte=date_to)

	total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
	today = timezone.localdate()
	start_of_month = today.replace(day=1)
	month_expenses = Expense.objects.filter(expense_date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or 0
	start_of_week = today - timedelta(days=today.weekday())
	week_expenses = Expense.objects.filter(expense_date__gte=start_of_week).aggregate(total=Sum('amount'))['total'] or 0

	paginator = Paginator(expenses, 30)
	page_obj = paginator.get_page(request.GET.get('page'))

	expenses_by_category = expenses.values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total')

	return render(
		request,
		'accounts/expense_list.html',
		{
			'expenses': page_obj,
			'categories': ExpenseCategory.objects.filter(is_active=True),
			'total_expenses': total_expenses,
			'month_expenses': month_expenses,
			'week_expenses': week_expenses,
			'expenses_by_category': expenses_by_category,
			'date_from': date_from,
			'date_to': date_to,
			'selected_category': category_id,
			'selected_payment': payment_method,
		},
	)


@login_required
def expense_create(request):
	if request.method == 'POST':
		form = ExpenseForm(request.POST, request.FILES)
		if form.is_valid():
			expense = form.save(commit=False)
			expense.created_by = request.user
			expense.save()
			messages.success(request, f'تم إضافة المصروف بنجاح: {expense.category.name} - {expense.amount} ريال')
			return redirect('accounts:expense_list')
		messages.error(request, 'حدث خطأ في إدخال البيانات، يرجى التحقق.')
	else:
		form = ExpenseForm()

	today = timezone.localdate()
	categories_stats = []
	for category in ExpenseCategory.objects.filter(is_active=True):
		month_total = Expense.objects.filter(category=category, expense_date__year=today.year, expense_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
		categories_stats.append({'name': category.name, 'month_total': month_total, 'color': category.color})

	month_expenses = Expense.objects.filter(expense_date__year=today.year, expense_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0

	return render(
		request,
		'accounts/expense_form.html',
		{
			'form': form,
			'title': 'إضافة مصروف جديد',
			'categories_stats': categories_stats,
			'month_expenses': month_expenses,
		},
	)


@login_required
@require_http_methods(['GET'])
def get_category_details(request, category_id):
	category = get_object_or_404(ExpenseCategory, id=category_id, is_active=True)
	avg_amount = Expense.objects.filter(category=category).aggregate(avg=Avg('amount'))['avg'] or 0
	return JsonResponse(
		{
			'success': True,
			'category': {
				'id': category.id,
				'name': category.name,
				'category_type': category.get_category_type_display(),
				'description': category.description,
				'icon': category.icon,
				'color': category.color,
				'avg_amount': float(avg_amount),
			},
		}
	)


@login_required
def expense_edit(request, pk):
	expense = get_object_or_404(Expense, pk=pk)
	if request.method == 'POST':
		form = ExpenseForm(request.POST, request.FILES, instance=expense)
		if form.is_valid():
			form.save()
			messages.success(request, 'تم تعديل المصروف بنجاح')
			return redirect('accounts:expense_list')
	else:
		form = ExpenseForm(instance=expense)

	today = timezone.localdate()
	categories_stats = []
	for category in ExpenseCategory.objects.filter(is_active=True):
		month_total = Expense.objects.filter(category=category, expense_date__year=today.year, expense_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
		categories_stats.append({'name': category.name, 'month_total': month_total, 'color': category.color})

	month_expenses = Expense.objects.filter(expense_date__year=today.year, expense_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0

	return render(
		request,
		'accounts/expense_form.html',
		{
			'form': form,
			'title': 'تعديل مصروف',
			'expense': expense,
			'categories_stats': categories_stats,
			'month_expenses': month_expenses,
		},
	)


@login_required
def expense_delete(request, pk):
	expense = get_object_or_404(Expense, pk=pk)
	if request.method == 'POST':
		expense.delete()
		messages.success(request, 'تم حذف المصروف بنجاح')
		return redirect('accounts:expense_list')
	return render(request, 'accounts/expense_confirm_delete.html', {'expense': expense})


@login_required
def expense_category_list(request):
	categories = ExpenseCategory.objects.all().order_by('name')
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, f"تم إضافة الفئة {form.cleaned_data['name']} بنجاح")
			return redirect('accounts:expense_category_list')
	else:
		form = ExpenseCategoryForm()

	for category in categories:
		category.total_expenses = category.expense_set.aggregate(total=Sum('amount'))['total'] or 0
		category.expense_count = category.expense_set.count()

	return render(request, 'accounts/expense_category_list.html', {'categories': categories, 'form': form})


@login_required
def expense_category_edit(request, pk):
	category = get_object_or_404(ExpenseCategory, pk=pk)
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST, instance=category)
		if form.is_valid():
			form.save()
			messages.success(request, f'تم تعديل الفئة {category.name} بنجاح')
			return redirect('accounts:expense_category_list')
	else:
		form = ExpenseCategoryForm(instance=category)

	return render(request, 'accounts/expense_category_form.html', {'form': form, 'category': category, 'title': 'تعديل فئة المصروف'})


@login_required
def get_expense_statistics(request):
	months = []
	monthly_totals = []
	today = timezone.localdate()
	for i in range(11, -1, -1):
		month_anchor = (today.replace(day=1) - timedelta(days=31 * i)).replace(day=1)
		month_total = Expense.objects.filter(expense_date__year=month_anchor.year, expense_date__month=month_anchor.month).aggregate(total=Sum('amount'))['total'] or 0
		months.append(month_anchor.strftime('%Y-%m'))
		monthly_totals.append(float(month_total))

	today_total = Expense.objects.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or 0
	top_expenses = Expense.objects.select_related('category').order_by('-amount')[:5]
	top_expenses_data = [
		{
			'description': expense.description,
			'amount': float(expense.amount),
			'category': expense.category.name,
			'date': expense.expense_date.strftime('%Y-%m-%d'),
		}
		for expense in top_expenses
	]

	return JsonResponse(
		{
			'success': True,
			'months': months,
			'monthly_totals': monthly_totals,
			'today_total': float(today_total),
			'top_expenses': top_expenses_data,
		}
	)


@login_required
@user_passes_test(lambda user: user.is_superuser)
def user_list(request):
	users = User.objects.prefetch_related('groups').all().order_by('username')
	return render(request, 'accounts/user_list.html', {'users': users})


@login_required
@user_passes_test(lambda user: user.is_superuser)
def user_create(request):
	form = UserCreationForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		user = form.save()
		group_id = request.POST.get('group')
		if group_id:
			group = Group.objects.filter(id=group_id).first()
			if group:
				user.groups.add(group)
		messages.success(request, f'تم إنشاء المستخدم {user.username} بنجاح')
		return redirect('accounts:user_list')

	return render(request, 'accounts/user_form.html', {'form': form, 'groups': Group.objects.all()})
