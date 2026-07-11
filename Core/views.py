from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import SchoolConfiguration
from .models import AcademicSession, Term
from Accounts.views import AdminRequiredMixin # We reuse our custom mixin

class SessionListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = AcademicSession
    template_name = 'core/session_list.html'
    context_object_name = 'sessions'

class SessionCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = AcademicSession
    fields = ['name', 'is_current']
    template_name = 'core/session_form.html'
    success_url = reverse_lazy('session_list')

class TermCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Term
    fields = ['session', 'name', 'is_current']
    template_name = 'core/term_form.html'
    success_url = reverse_lazy('session_list')

class SchoolConfigUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = SchoolConfiguration
    fields = ['school_name', 'school_motto', 'address', 'logo']
    template_name = 'core/school_config_form.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        # Always return the first (and only) config object
        return SchoolConfiguration.objects.first()