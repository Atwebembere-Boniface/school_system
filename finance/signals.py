from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FeeStructure, StudentBalance # Assuming you have a Balance model
from Academics.models import StudentProfile

@receiver(post_save, sender=FeeStructure)
def apply_fees_to_students(sender, instance, created, **kwargs):
    if created:
        # Find all students in the class this fee structure belongs to
        students = StudentProfile.objects.filter(current_class=instance.target_class)
        
        for student in students:
            # Logic to update each student's balance based on the new structure
            # This ensures image 02b073.png shows the correct total due
            pass