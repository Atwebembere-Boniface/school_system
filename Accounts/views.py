from django.urls import reverse_lazy
from django.views.generic import CreateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import UserRegistrationForm
from .models import User

class AdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to only Admin users"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == User.ADMIN

# --- DASHBOARD DISPATCHER ---

class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """
    The 'Traffic Controller' view. 
    Point your LOGIN_REDIRECT_URL in settings.py to this view.
    """
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        role = str(user.role).upper() 
        
        # Admin logic
        if role == 'ADMIN':
            return reverse_lazy('academics:admin_dashboard') 
        
        # Teacher logic
        elif role == 'TEACHER':
            return reverse_lazy('academics:teacher_dashboard')
            
        # Student logic
        elif role == 'STUDENT':
            return reverse_lazy('academics:student_dashboard')
            
        # Bursar logic - Redirecting to the Finance App
        elif role == 'BURSAR':
            # Note: Ensure 'finance:bursar_dashboard' or 'finance:bursar_class_list' 
            # is defined in finance/urls.py
            return reverse_lazy('finance:bursar_dashboard') 
            
        # Fallback for unknown roles
        return reverse_lazy('login')

# --- REGISTRATION VIEWS ---

class UserRegisterView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('academics:dashboard_dispatch')

class BursarRegistrationView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Consolidated view for registering Bursars with correct status and role"""
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register_bursar.html'
    success_url = reverse_lazy('academics:admin_dashboard')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = User.BURSAR  # Constant from your User model
        user.is_active = True    # Ensures they can log in immediately
        user.save()
        return super().form_valid(form)