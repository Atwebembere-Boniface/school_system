import uuid
import json
import requests
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from .forms import BursarPaymentForm
from django.contrib import messages

# Internal Imports
from Academics.models import ClassLevel, StudentProfile
from .models import Payment, FeeStructure
from .utils import get_student_financial_summary

# --- PERMISSIONS ---

class BursarRequiredMixin(UserPassesTestMixin):
    """Restricts access to only users with the BURSAR role or Superusers."""
    def test_func(self):
        return self.request.user.role == 'BURSAR' or self.request.user.is_superuser

# --- BURSAR VIEWS ---

class BursarClassListView(LoginRequiredMixin, BursarRequiredMixin, ListView):
    model = ClassLevel
    template_name = 'finance/bursar_class_list.html'
    context_object_name = 'classes'

class StudentFinancialDetailView(LoginRequiredMixin, BursarRequiredMixin, DetailView):
    model = StudentProfile
    template_name = 'finance/student_finance_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dynamic financial calculation via utility
        context['summary'] = get_student_financial_summary(self.object)
        context['payments'] = self.object.payments.all().order_by('-created_at')
        return context

class FeeStructureCreateView(LoginRequiredMixin, BursarRequiredMixin, CreateView):
    model = FeeStructure
    fields = ['target_class', 'term', 'academic_year', 'tuition_fees', 'other_charges', 'is_active']
    template_name = 'finance/fee_structure_form.html'
    success_url = reverse_lazy('finance:bursar_class_list')

    def form_valid(self, form):
        # Business Logic: Deactivate existing active structures for this class/term
        if form.cleaned_data.get('is_active'):
            FeeStructure.objects.filter(
                target_class=form.cleaned_data.get('target_class'),
                term=form.cleaned_data.get('term'),
                is_active=True
            ).update(is_active=False)
        return super().form_valid(form)

# --- STUDENT VIEWS ---

class StudentFinanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'academics/student_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Safer way to get the profile without crashing
        student = getattr(self.request.user, 'studentprofile', None)
        
        if student:
            context['summary'] = get_student_financial_summary(student)
            context['payment_history'] = Payment.objects.filter(student=student).order_by('-created_at')
        else:
            context['summary'] = None
            context['payment_history'] = []
            context['error_message'] = "No student profile found for this account."
            
        return context
    

class InitiatePaymentView(LoginRequiredMixin, CreateView):
    model = Payment
    fields = ['amount', 'phone_number']
    template_name = 'finance/initiate_payment.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Broadened check to ensure students aren't locked out.
        Checks for both the attribute and the user role.
        """
        # We check both the relationship and the role field as a fallback
        is_student = hasattr(request.user, 'studentprofile') or getattr(request.user, 'role', None) == 'STUDENT'
        
        if not is_student:
            messages.error(request, "Access denied. Only students can use this payment page.")
            return redirect('finance:bursar_dashboard')
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Handles the logic when the form is submitted.
        Includes a safety fallback for profile lookup.
        """
        try:
            # Try the standard related name
            form.instance.student = self.request.user.studentprofile
        except AttributeError:
            # Fallback: Manually look up the profile if the attribute isn't on the user object
            from Academics.models import StudentProfile
            form.instance.student = StudentProfile.objects.get(user=self.request.user)

        # Set transaction metadata
        form.instance.transaction_reference = str(uuid.uuid4())
        form.instance.status = 'PENDING'
        form.instance.payment_method = 'MM'  # Default to Mobile Money for self-pay
        
        messages.success(self.request, "Payment initiated. Please check your phone for the prompt.")
        return super().form_valid(form)

    def get_success_url(self):
        """Redirects back to the student's finance dashboard upon success."""
        return reverse_lazy('finance:student_dashboard')
    
# --- EXTERNAL GATEWAY WEBHOOK ---



@csrf_exempt
def payment_webhook(request):
    """
    Receives success/failure notifications from the payment gateway (Sandbox).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Match the reference used in InitiatePaymentView
            ref = data.get('tx_ref') 
            status = data.get('status')
            
            if ref:
                payment = Payment.objects.get(transaction_reference=ref)
                if status == 'successful':
                    payment.status = 'SUCCESS'
                else:
                    payment.status = 'FAILED'
                payment.save()
                
            return HttpResponse(status=200)
        except (json.JSONDecodeError, Payment.DoesNotExist):
            return HttpResponse(status=400)
    return HttpResponse(status=405)



class BursarClassDetailView(LoginRequiredMixin, BursarRequiredMixin, DetailView):
    model = ClassLevel
    template_name = 'finance/bursar_class_detail.html'
    context_object_name = 'selected_class'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch all students in this class
        students = StudentProfile.objects.filter(current_class=self.object).select_related('user')
        
        # We'll calculate financial summaries for each student in the list
        student_data = []
        for student in students:
            summary = get_student_financial_summary(student)
            student_data.append({
                'profile': student,
                'summary': summary
            })
            
        context['student_finance_list'] = student_data
        return context
    


class BursarRecordPaymentView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Payment
    form_class = BursarPaymentForm
    template_name = 'finance/bursar_record_payment.html'
    
    def test_func(self):
        # Only allow Bursars and Admins to access this view
        return self.request.user.role in ['BURSAR', 'ADMIN']

    def form_valid(self, form):
        # We don't use request.user.studentprofile here
        payment = form.save(commit=False)
        
        # Assign the currently logged-in user (the Bursar) to 'recorded_by'
        payment.recorded_by = self.request.user
        payment.status = 'SUCCESS'  # Usually success if recorded manually
        payment.save()
        
        messages.success(self.request, f"Payment of {payment.amount} recorded for {payment.student}")
        return redirect('finance:bursar_dashboard')    


class BursarDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = StudentProfile
    template_name = 'finance/bursar_dashboard.html'
    context_object_name = 'students'

    def test_func(self):
        # Match the permission logic from your record view
        return self.request.user.role in ['BURSAR', 'ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch recent payments for the dashboard table
        context['recent_payments'] = Payment.objects.all().order_by('-created_at')[:10]
        return context