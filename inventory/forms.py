from django import forms

from .models import Product, StockMovement, Supplier


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'type',
            'category',
            'sku',
            'barcode',
            'quantity',
            'min_stock',
            'purchase_price',
            'selling_price',
            'is_fresh',
            'harvest_date',
            'shelf_life_hours',
            'storage_temp',
            'is_seasonal',
            'image',
            'description',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنتج'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رمز المنتج (اختياري)'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الباركود'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'harvest_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shelf_life_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'storage_temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('type') == 'flower':
            if not cleaned_data.get('harvest_date'):
                self.add_error('harvest_date', 'الورد يحتاج إلى تاريخ القطف')
            if not cleaned_data.get('shelf_life_hours'):
                self.add_error('shelf_life_hours', 'الورد يحتاج إلى عدد ساعات الصلاحية')
        return cleaned_data


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address', 'contact_person', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockAdjustForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['quantity', 'movement_type', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
