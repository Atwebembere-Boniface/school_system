from django import forms
from .models import Payment
from Academics.models import StudentProfile

class BursarPaymentForm(forms.ModelForm):
    # Allow the bursar to select from all active students
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.all(),
        label="Select Student",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Payment
        # Matches your updated Payment model fields exactly
        fields = ['student', 'amount', 'payment_method', 'transaction_reference', 'phone_number']
        
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Receipt or Tx ID'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional for Cash'}),
        }

    def clean_transaction_reference(self):
        """Ensures the receipt/transaction ID isn't reused."""
        ref = self.cleaned_data.get('transaction_reference')
        if Payment.objects.filter(transaction_reference=ref).exists():
            raise forms.ValidationError("This Transaction Reference/Receipt ID has already been used.")
        return ref