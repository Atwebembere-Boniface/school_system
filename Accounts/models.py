from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    ADMIN = 'ADMIN'
    TEACHER = 'TEACHER'
    STUDENT = 'STUDENT'
    BURSAR = 'BURSAR'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
        (BURSAR, 'Bursar'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ADMIN)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    @property
    def is_bursar(self):
        return self.role == self.BURSAR

    def __str__(self):
        return f"{self.username} - {self.role}"

class StudentProfile(models.Model):
    DAY = 'DAY'
    BOARDING = 'BOARDING'
    STUDENT_TYPE_CHOICES = [
        (DAY, 'Day Student'),
        (BOARDING, 'Boarding Student'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')

    # Added related_name='accounts_student_profiles' to fix the E304 clash
    current_class = models.ForeignKey(
        'Academics.ClassLevel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts_student_profiles'

    )


    registration_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    student_type = models.CharField(max_length=10, choices=STUDENT_TYPE_CHOICES, default=DAY)

    def __str__(self):
        return f"Profile: {self.user.get_full_name() or self.user.username}"

# --- SIGNALS: Cleaned up and combined ---


@receiver(post_save, sender=User)
def manage_student_profile(sender, instance, created, **kwargs):
    """
    Creates a profile only if the user role is STUDENT.
    Saves the profile on subsequent updates if it exists.
    """
    if instance.role == User.STUDENT:
        if created:
            StudentProfile.objects.create(user=instance)
        else:
            # hasattr checks if the profile exists before trying to save it
            if hasattr(instance, 'student_profile'):
                instance.student_profile.save()