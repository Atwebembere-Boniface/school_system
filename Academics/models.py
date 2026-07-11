from django.db import models
from django.conf import settings
from django.utils import timezone

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class ClassLevel(models.Model):
    name = models.CharField(max_length=50) 
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role': 'TEACHER'}
    )

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    # Choices for Student Type
    TYPE_CHOICES = [
        ('DAY', 'Day Student'), 
        ('BOARDING', 'Boarding Student')
    ]

    # ADD THIS: Choices for Gender
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'STUDENT'},
        related_name='academic_profile'
    )
    registration_number = models.CharField(max_length=20, unique=True)
    current_class = models.ForeignKey(
        'ClassLevel', 
        on_delete=models.PROTECT,
        related_name='academic_student_profiles'
    )
    student_type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES, 
        default='DAY'
    )

    # ADD THIS FIELD:
    gender = models.CharField(
        max_length=10, 
        choices=GENDER_CHOICES, 
        default='MALE'
    )
    
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()

    def __str__(self):
        # Optional: Updated __str__ to include gender display
        return f"{self.user.get_full_name()} - {self.registration_number} ({self.get_gender_display()})"
    

    
class CourseAssignment(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'TEACHER'})
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_levels = models.ManyToManyField(ClassLevel, related_name='course_assignments')
    academic_session = models.ForeignKey('Core.AcademicSession', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'subject', 'academic_session')

    def __str__(self):
        classes = ", ".join([cl.name for cl in self.class_levels.all()])
        return f"{self.subject.name} ({classes})"

class Material(models.Model):
    # This is the primary model for all student resources
    MATERIAL_TYPES = (
        ('notes', 'Notes'),
        ('assignment', 'Assignment'),
        ('test', 'Test/Quiz'),
    )
    
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='materials/%Y/%m/')
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    
    # Connects to the specific teacher/subject session
    assignment = models.ForeignKey('CourseAssignment', on_delete=models.CASCADE, related_name='materials')
    
    # Allows a teacher to upload once but target multiple classes (e.g., S1A and S1B)
    target_classes = models.ManyToManyField('ClassLevel', related_name='class_materials', blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    downloads = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.get_material_type_display()})"

# --- REMOVED StudyMaterial and SubjectResource to avoid confusion ---
# Use Material for everything to ensure the filters in views.py work.

class Timetable(models.Model):
    class_level = models.OneToOneField(ClassLevel, on_delete=models.CASCADE, related_name='timetable')
    file = models.FileField(upload_to='timetables/')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Timetable for {self.class_level.name}"

class Result(models.Model):
    assignment = models.ForeignKey(CourseAssignment, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='results')
    score = models.PositiveIntegerField(help_text="Enter mark out of 100")
    grade = models.CharField(max_length=5, blank=True)
    # NEW FIELD: Added to store the numerical value of the grade for calculations
    grade_point = models.PositiveIntegerField(default=9, blank=True) 
    description = models.CharField(max_length=50, blank=True)
    term = models.CharField(max_length=20, choices=[('TERM 1', 'Term 1'), ('TERM 2', 'Term 2'), ('TERM 3', 'Term 3')])
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Updated grading logic to include grade_point values
        if self.score >= 80: 
            self.grade, self.grade_point, self.description = 'D1', 1, 'Distinction 1'
        elif self.score >= 75: 
            self.grade, self.grade_point, self.description = 'D2', 2, 'Distinction 2'
        elif self.score >= 70: 
            self.grade, self.grade_point, self.description = 'C3', 3, 'Credit 3'
        elif self.score >= 65: 
            self.grade, self.grade_point, self.description = 'C4', 4, 'Credit 4'
        elif self.score >= 60: 
            self.grade, self.grade_point, self.description = 'C5', 5, 'Credit 5'
        elif self.score >= 55: 
            self.grade, self.grade_point, self.description = 'C6', 6, 'Credit 6'
        elif self.score >= 50: 
            self.grade, self.grade_point, self.description = 'P7', 7, 'Pass 7'
        elif self.score >= 45: 
            self.grade, self.grade_point, self.description = 'P8', 8, 'Pass 8'
        else: 
            self.grade, self.grade_point, self.description = 'F9', 9, 'Fail'
            
        super().save(*args, **kwargs)