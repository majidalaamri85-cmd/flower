from django import forms

from .models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'category',
            'amount',
            'description',
            'payment_method',
            'receipt',
            'receipt_number',
            'expense_date',
            'notes',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'expenseCategory'}),
            'amount': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': 'المبلغ بالريال العماني',
                }
            ),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'وصف المصروف'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الإيصال'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ملاحظات إضافية...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        self.fields['category'].empty_label = '--- اختر فئة المصروف ---'


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'category_type', 'description', 'icon', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'مثال: إيجار المحل، فواتير كهرباء...'}
            ),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'وصف الفئة...'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-home'}),
            'color': forms.Select(
                attrs={'class': 'form-select'},
                choices=[
                    ('primary', 'أزرق'),
                    ('success', 'أخضر'),
                    ('danger', 'أحمر'),
                    ('warning', 'أصفر'),
                    ('info', 'سماوي'),
                    ('secondary', 'رمادي'),
                    ('dark', 'داكن'),
                ],
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
