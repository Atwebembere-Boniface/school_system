from django.db.models import Sum
from .models import FeeStructure, Payment

def get_student_financial_summary(student):
    # Get active fee structure for the student's class
    fee = FeeStructure.objects.filter(target_class=student.current_class, is_active=True).first()
    total_required = fee.total_amount() if fee else 0
    
    # Calculate total successful payments
    total_paid = Payment.objects.filter(
        student=student, 
        status='SUCCESS'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return {
        'total_required': total_required,
        'total_paid': total_paid,
        'balance': total_required - total_paid,
        'fee_structure': fee
    }