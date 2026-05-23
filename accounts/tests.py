from decimal import Decimal

from django.test import TestCase

from .models import Expense, ExpenseCategory


class ExpenseModelTests(TestCase):
	def test_expense_string_representation(self):
		category = ExpenseCategory.objects.create(name='تشغيل', description='')
		expense = Expense.objects.create(
			category=category,
			amount=Decimal('150.50'),
			description='فاتورة كهرباء',
		)

		self.assertIn('تشغيل - 150.50 ر.ع', str(expense))
