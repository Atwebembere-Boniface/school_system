from django.db import models

class SchoolConfiguration(models.Model):
    school_name = models.CharField(max_length=255, default="Nyabuhikye SS")
    school_motto = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to='school_info/', blank=True, null=True)

    def __str__(self):
        return self.school_name

class AcademicSession(models.Model):
    """Represents a Year, e.g., 2025, 2026"""
    name = models.CharField(max_length=10, unique=True) # e.g., "2026"
    is_current = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Term(models.Model):
    TERM_CHOICES = [
        ('1', 'Term I'),
        ('2', 'Term II'),
        ('3', 'Term III'),
    ]
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    name = models.CharField(max_length=1, choices=TERM_CHOICES)
    is_current = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_current:
            Term.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_name_display()} ({self.session.name})"