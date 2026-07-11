from .models import SchoolConfiguration, AcademicSession, Term

def school_info(request):
    return {
        'school_cfg': SchoolConfiguration.objects.first(),
        'current_session': AcademicSession.objects.filter(is_current=True).first(),
        'current_term': Term.objects.filter(is_current=True).first(),
    }