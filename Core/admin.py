from django.contrib import admin
from .models import SchoolConfiguration, AcademicSession, Term

@admin.register(SchoolConfiguration)
class SchoolConfigurationAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'school_motto')

    # Prevent creating multiple school profiles; only allow editing one
    def has_add_permission(self, request):
        return not SchoolConfiguration.objects.exists()

@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current')

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'is_current')
    list_filter = ('session',)