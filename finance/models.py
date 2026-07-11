from django.db import models
from Academics.models import StudentProfile, ClassLevel # Coordinating with your existing apps
from django.conf import settings

class FeeStructure(models.Model):
    target_class = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='fee_structures')
    term = models.CharField(max_length=20, choices=[('TERM 1', 'Term 1'), ('TERM 2', 'Term 2'), ('TERM 3', 'Term 3')])
    academic_year = models.IntegerField(default=2026)
    tuition_fees = models.DecimalField(max_digits=10, decimal_places=2)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('target_class', 'term', 'academic_year')

    def total_amount(self):
        return self.tuition_fees + self.other_charges

    def __str__(self):
        return f"{self.target_class.name} - {self.term} ({self.academic_year})"

class Payment(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')]
    
    # New choices for the Bursar to select from
    METHOD_CHOICES = [('CASH', 'Cash'), ('MM', 'Mobile Money'), ('BANK', 'Bank Deposit')]
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15, blank=True, null=True) # Optional for Cash
    
    # Renamed to match the field your model already has
    transaction_reference = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='CASH')
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # Tracking who received the money
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.amount} ({self.status})"