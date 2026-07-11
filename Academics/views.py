from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, RedirectView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from Accounts.views import AdminRequiredMixin
from .models import Subject, ClassLevel, StudentProfile, CourseAssignment, Material, Timetable
from .models import Result
from Accounts.models import StudentProfile as AccountStudentProfile
from django.db import models
from .forms import StudentRegistrationForm, CourseAssignmentForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .forms import BulkMarkForm, MaterialUploadForm
from django.forms import modelformset_factory
from django.views import View
from django.http import HttpResponse
import openpyxl
from django.urls import reverse, reverse_lazy
from .utils import ReportCalculator
from django.http import HttpResponseRedirect
from django.contrib import messages
from .forms import StudentEditForm
from django.db.models import Avg
from django.db.models import Avg, Sum, Max, Min, Count
from finance.utils import get_student_financial_summary

# --- DASHBOARDS ---

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Provides the main control panel for school administrators."""
    template_name = 'accounts/admin_dashboard.html'

class TeacherDashboardView(LoginRequiredMixin, ListView):
    model = CourseAssignment
    template_name = 'academics/teacher_dashboard.html'
    context_object_name = 'my_load'

    def get_queryset(self):
        # 1. Remove 'class_level' from select_related (it's no longer a ForeignKey)
        # 2. Add prefetch_related('class_levels') for the ManyToMany field
        return CourseAssignment.objects.filter(
            teacher=self.request.user
        ).select_related(
            'subject', 
            'academic_session'
        ).prefetch_related(
            'class_levels'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fetch the 5 most recent uploads by this teacher
        context['recent_uploads'] = Material.objects.filter(
            assignment__teacher=self.request.user
        ).order_by('-uploaded_at')[:5]
        
        # Fetch classes where this user is the official Class Teacher
        context['managed_classes'] = ClassLevel.objects.filter(
            class_teacher=self.request.user
        )
        
        return context
    
class StudentDashboardView(LoginRequiredMixin, ListView):
    template_name = 'academics/student_dashboard.html'
    context_object_name = 'my_teachers'

    def get_queryset(self):
        try:
            # Look for academic_profile or studentprofile based on your User model relationship
            profile = getattr(self.request.user, 'academic_profile', None) or getattr(self.request.user, 'studentprofile', None)
            if profile and profile.current_class:
                return CourseAssignment.objects.filter(class_levels=profile.current_class).distinct()
        except Exception:
            pass
        return CourseAssignment.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # 1. Identify the student profile using safer lookups
            profile = getattr(self.request.user, 'studentprofile', None) or getattr(self.request.user, 'academic_profile', None)
            context['student'] = profile

            if profile:
                # 2. Fetch Finance Data (Ensure 'Finance.utils' is imported)
                context['finance'] = get_student_financial_summary(profile)

                # 3. Fetch Academic Data only if they have an assigned class
                if profile.current_class:
                    context['timetable'] = Timetable.objects.filter(class_level=profile.current_class).first()

                    # Fetch assignments for the class
                    assignments = CourseAssignment.objects.filter(
                        class_levels=profile.current_class
                    ).select_related('subject', 'teacher').distinct()

                    subjects_with_notes = []
                    for assign in assignments:
                        # Get materials filtered by class or global
                        materials = Material.objects.filter(
                            assignment__subject=assign.subject
                        ).filter(
                            models.Q(target_classes=profile.current_class) | 
                            models.Q(target_classes__isnull=True)
                        ).distinct()

                        subjects_with_notes.append({
                            'assignment': assign,
                            'note_count': materials.filter(material_type__iexact='notes').count(),
                            'assignment_count': materials.filter(material_type__iexact='assignment').count(),
                        })
                    context['subjects_with_notes'] = subjects_with_notes
                else:
                    context['subjects_with_notes'] = []
            
        except Exception as e:
            # Safe fallbacks if any database query fails
            context['student'] = None
            context['finance'] = None
            context['subjects_with_notes'] = []
            # print(f"Error: {e}") 

        return context
    
class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        # Ensures internal redirects use the 'academics' namespace
        if user.role == 'ADMIN':
            return reverse_lazy('academics:admin_dashboard') 
        elif user.role == 'TEACHER':
            return reverse_lazy('academics:teacher_dashboard')
        elif user.role == 'STUDENT':
            return reverse_lazy('academics:student_dashboard')
        return reverse_lazy('account:login')

# --- SUBJECTS & CLASSES ---

class SubjectListView(LoginRequiredMixin, ListView):
    model = Subject
    context_object_name = 'subjects'

class SubjectCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Subject
    fields = ['name', 'code']
    success_url = reverse_lazy('academics:subject_list')

class ClassListView(LoginRequiredMixin, ListView):
    model = ClassLevel
    template_name = 'academics/class_list.html'
    context_object_name = 'classes'

class ClassCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ClassLevel
    fields = ['name', 'class_teacher']
    template_name = 'academics/class_form.html'
    success_url = reverse_lazy('academics:class_list')

class ClassDetailView(LoginRequiredMixin, DetailView):
    model = ClassLevel
    template_name = 'academics/class_detail.html'
    context_object_name = 'class_obj'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all active students for this class once
        students = self.object.academic_student_profiles.filter(deleted_at__isnull=True)
        
        # Add data to context
        context['active_students'] = students
        context['total_count'] = students.count()
        context['boarding_count'] = students.filter(student_type='BOARDING').count()
        context['day_count'] = students.filter(student_type='DAY').count()
        
        return context
    

# --- STUDENT MANAGEMENT ---

class StudentCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = StudentProfile
    form_class = StudentRegistrationForm
    template_name = 'academics/student_form.html'

    # This must match your urls.py name 'class_list'
    success_url = reverse_lazy('academics:class_list')

    def form_valid(self, form):
        # 1. Trigger the form's custom save (Creates User + Profile)
        self.object = form.save()

        # 2. Success message
        messages.success(self.request, "Student registered successfully!")

        # 3. CRITICAL: Manual redirect to bypass the standard CreateView logic
        # DO NOT call super().form_valid(form)
        return HttpResponseRedirect(self.get_success_url())



class StudentUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = StudentProfile
    # Use the form class instead of 'fields' to include User and Gender logic
    form_class = StudentEditForm 
    template_name = 'academics/generic_form.html'
    success_url = reverse_lazy('academics:all_students_list')

    def get_initial(self):
        """
        Pre-populates the first_name and last_name fields in the form
        using data from the related User model.
        """
        initial = super().get_initial()
        if self.object and self.object.user:
            initial['first_name'] = self.object.user.first_name
            initial['last_name'] = self.object.user.last_name
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Update Student: {self.object.user.get_full_name()}"
        context['button_text'] = "Save Changes"
        return context

class StudentDetailView(LoginRequiredMixin, DetailView):
    model = StudentProfile
    template_name = 'academics/student_profile.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Fetch results using the correct relationship path
        # assignment is a ForeignKey, so we can follow it to the subject
        results = Result.objects.filter(student=self.object).select_related(
            'assignment__subject'
        )
        context['results'] = results
        
        # 2. Calculate average score
        stats = results.aggregate(avg=Avg('score'))
        context['average_score'] = stats['avg'] or 0
        
        return context    

class StudentDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = StudentProfile
    template_name = 'academics/confirm_delete.html'
    success_url = reverse_lazy('academics:class_list')

    def form_valid(self, form):
        self.object.soft_delete()
        messages.warning(self.request, f"Student {self.object} moved to Recycle Bin.")
        return redirect(self.get_success_url())

# --- RECYCLE BIN ---

class RecycleBinListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = StudentProfile
    template_name = 'academics/recycle_bin.html'
    context_object_name = 'deleted_students'

    def get_queryset(self):
        return StudentProfile.objects.filter(deleted_at__isnull=False)

def restore_student(request, pk):
    student = get_object_or_404(StudentProfile, pk=pk)
    student.restore()
    messages.success(request, f"Student {student.user.get_full_name()} restored.")
    return redirect('academics:recycle_bin')

def permanent_delete_student(request, pk):
    student = get_object_or_404(StudentProfile, pk=pk)
    user = student.user
    student.delete()
    user.delete()
    messages.error(request, "Records purged permanently.")
    return redirect('academics:recycle_bin')

# --- ASSIGNMENTS & MATERIALS ---

class CourseAssignmentCreateView(LoginRequiredMixin, CreateView):
    model = CourseAssignment
    form_class = CourseAssignmentForm # Use the form_class instead of 'fields'
    template_name = 'academics/courseassignment_form.html'
    success_url = reverse_lazy('academics:assignment_list')

class CourseAssignmentDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = CourseAssignment
    template_name = 'academics/confirm_delete.html'
    success_url = reverse_lazy('academics:teacher_dashboard')

class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    fields = ['title', 'file', 'material_type', 'assignment']
    template_name = 'academics/material_form.html'
    success_url = reverse_lazy('academics:teacher_dashboard')

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['assignment'].queryset = CourseAssignment.objects.filter(teacher=self.request.user)
        return form

class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    success_url = reverse_lazy('academics:teacher_dashboard')

    def get_queryset(self):
        return self.model.objects.filter(assignment__teacher=self.request.user)

# --- CLASS TEACHER PERMISSIONS ---

class ClassStaffListView(LoginRequiredMixin, ListView):
    model = CourseAssignment
    template_name = 'academics/class_staff_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        # Use 'pk' to match your path 'class/<int:pk>/staff/'
        pk = self.kwargs.get('pk') 
        self.class_level = get_object_or_404(ClassLevel, pk=pk)
        
        return CourseAssignment.objects.filter(
            class_levels=self.class_level
        ).select_related('teacher', 'subject')    

class AssignedClassStudentListView(LoginRequiredMixin, ListView):
    model = StudentProfile
    template_name = 'academics/assigned_students.html'
    context_object_name = 'students'

    def get_queryset(self):
        # Use the ID from the URL to get students for that specific class
        class_id = self.kwargs.get('pk')
        return StudentProfile.objects.filter(
            current_class_id=class_id
        ).select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the class object to context so the template knows which class this is
        context['target_class'] = ClassLevel.objects.get(pk=self.kwargs.get('pk'))
        return context


class CourseAssignmentUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = CourseAssignment
    form_class = CourseAssignmentForm # Use the form that handles ManyToMany
    template_name = 'academics/courseassignment_form.html' # Reuse the same form template
    success_url = reverse_lazy('academics:assignment_list')
    

class AllStudentsListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = StudentProfile
    template_name = 'academics/all_students_list.html'
    context_object_name = 'students'

    def get_queryset(self):
        query = self.request.GET.get('q')
        # Optimized database query to prevent slow loading
        queryset = StudentProfile.objects.filter(
            deleted_at__isnull=True
        ).select_related('user', 'current_class')
        
        if query:
            # Search by Name or Registration Number
            queryset = queryset.filter(
                models.Q(user__first_name__icontains=query) | 
                models.Q(user__last_name__icontains=query) | 
                models.Q(registration_number__icontains=query)
            )
        return queryset.order_by('current_class', 'user__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use the filtered queryset to keep counts accurate during search
        current_queryset = self.get_queryset()
        
        # General Statistics
        context['total_count'] = current_queryset.count()
        context['boarding_count'] = current_queryset.filter(student_type='BOARDING').count()
        context['day_count'] = current_queryset.filter(student_type='DAY').count()

        # Gender Statistics (Updated to match your template variables)
        context['male_count'] = current_queryset.filter(gender='MALE').count()
        context['female_count'] = current_queryset.filter(gender='FEMALE').count()
        
        return context
    

class AllStaffLoadListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CourseAssignment
    template_name = 'academics/all_staff_load.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        query = self.request.GET.get('q')
        
        # 1. Use select_related for ForeignKeys (teacher, subject, session)
        # 2. Use prefetch_related for ManyToMany (class_levels)
        queryset = CourseAssignment.objects.select_related(
            'teacher', 
            'subject', 
            'academic_session'
        ).prefetch_related(
            'class_levels'
        )

        if query:
            # Search for a teacher to see all their assigned classes
            queryset = queryset.filter(teacher__first_name__icontains=query)
            
        return queryset.order_by('teacher__first_name')
    
# timetable view
class TimetableUploadView(LoginRequiredMixin, CreateView):
    model = Timetable
    fields = ['file']
    template_name = 'academics/timetable_form.html'
    success_url = reverse_lazy('academics:teacher_dashboard')

    def form_valid(self, form):
        # Find the class where this user is the designated Class Teacher
        managed_class = get_object_or_404(ClassLevel, class_teacher=self.request.user)
        form.instance.class_level = managed_class
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Timetable updated successfully.")
        return super().form_valid(form)

class TimetableDeleteView(LoginRequiredMixin, DeleteView):
    model = Timetable
    success_url = reverse_lazy('academics:teacher_dashboard')

    def get_queryset(self):
        # Security: Only allow the class teacher to delete
        return self.model.objects.filter(class_level__class_teacher=self.request.user)   



class SubjectResourceListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'academics/subject_resources.html'
    context_object_name = 'materials'

    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        # Base: All materials for this subject
        queryset = Material.objects.filter(assignment__subject_id=subject_id)

        if self.request.user.role == 'STUDENT':
            profile = getattr(self.request.user, 'academic_profile', None) or getattr(self.request.user, 'studentprofile', None)
            
            if not profile or not profile.current_class:
                return Material.objects.none()

            # Security: Ensure student's class is assigned to this subject
            subject = get_object_or_404(Subject, id=subject_id)
            if not CourseAssignment.objects.filter(subject=subject, class_levels=profile.current_class).exists():
                raise PermissionDenied("You do not have access to this subject.")

            # Filter materials specifically for this student's class
            queryset = queryset.filter(
                models.Q(target_classes=profile.current_class) | models.Q(target_classes__isnull=True)
            )

        return queryset.distinct().order_by('-uploaded_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        materials = self.object_list 
        
        context['subject'] = get_object_or_404(Subject, id=self.kwargs['subject_id'])
        
        # Categorize using case-insensitive matching 
        context['notes'] = materials.filter(material_type__iexact='notes')
        context['assignments'] = materials.filter(material_type__iexact='assignment')
        context['tests'] = materials.filter(material_type__iexact='test')
        
        return context
    


class UploadMaterialView(LoginRequiredMixin, CreateView):
    model = Material
    fields = ['title', 'material_type', 'assignment', 'file']
    template_name = 'academics/upload_material.html'

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        # Filter the 'assignment' dropdown to only show this teacher's classes/subjects
        form.fields['assignment'].queryset = CourseAssignment.objects.filter(
            teacher=self.request.user
        )
        return form

    def form_valid(self, form):
        # Optional: any extra logic when saving
        return super().form_valid(form)
    


class TeacherMaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'academics/teacher_material_list.html'
    context_object_name = 'materials'

    def get_queryset(self):
        # Only show materials where the teacher is the one currently logged in
        return Material.objects.filter(assignment__teacher=self.request.user).order_by('-uploaded_at')

class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    success_url = reverse_lazy('academics:teacher_materials')
    template_name = 'academics/material_confirm_delete.html'

    def get_queryset(self):
        # Ensure teachers can only delete their own files for security
        return self.model.objects.filter(assignment__teacher=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Material deleted successfully.")
        return super().delete(request, *args, **kwargs)    
    


def track_material_download(request, pk):
    material = get_object_or_404(Material, pk=pk)
    # Increment the count
    material.downloads += 1
    material.save()
    # Redirect to the actual file location
    return redirect(material.file.url)

def track_timetable_download(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk)
    # Redirect to the actual file location
    return redirect(timetable.file.url)


class MarkEntryView(LoginRequiredMixin, CreateView):
    model = Result
    fields = ['student', 'score', 'term']
    template_name = 'academics/mark_entry.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 1. Get the specific assignment ID from the URL
        assignment = get_object_or_404(CourseAssignment, id=self.kwargs['assignment_id'])
        
        # 2. Filter the student list to ONLY show students in that specific class
        form.fields['student'].queryset = StudentProfile.objects.filter(
            current_class=assignment.class_level,
            deleted_at__isnull=True
        )
        return form

    def form_valid(self, form):
        # Automatically link the result to the correct assignment
        form.instance.assignment = get_object_or_404(CourseAssignment, id=self.kwargs['assignment_id'])
        messages.success(self.request, "Mark recorded successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('academics:teacher_dashboard')
    

class BulkMarkEntryView(LoginRequiredMixin, View):
    template_name = 'academics/bulk_mark_entry.html'

    def get_context_data(self, assignment_id, post_data=None):
        assignment = get_object_or_404(CourseAssignment, id=assignment_id)
        
        # 1. Identify which class we are entering marks for
        # It tries to get class_id from URL/GET, otherwise defaults to the first assigned class
        class_id = self.request.GET.get('class_id')
        if class_id:
            target_class = get_object_or_404(ClassLevel, id=class_id)
        else:
            target_class = assignment.class_levels.first()

        # 2. Fetch students for this specific target class
        students = StudentProfile.objects.filter(
            current_class=target_class, 
            deleted_at__isnull=True
        ).select_related('user')

        # 3. Fetch existing results for this assignment and this specific class
        existing_results = Result.objects.filter(
            assignment=assignment,
            student__current_class=target_class
        ).order_by('student__user__last_name')
        
        # 4. Define the FormSet
        MarkFormSet = modelformset_factory(Result, form=BulkMarkForm, extra=len(students))
        
        if post_data:
            formset = MarkFormSet(post_data)
        else:
            # Pre-populate with student IDs
            initial_data = [{'student': student.id, 'term': 'TERM 1'} for student in students]
            formset = MarkFormSet(queryset=Result.objects.none(), initial=initial_data)
        
        return {
            'formset': formset,
            'student_forms': zip(students, formset),
            'assignment': assignment,
            'target_class': target_class, # Added to template context
            'existing_results': existing_results
        }

    def get(self, request, assignment_id):
        context = self.get_context_data(assignment_id)
        return render(request, self.template_name, context)

    def post(self, request, assignment_id):
        context = self.get_context_data(assignment_id, post_data=request.POST)
        formset = context['formset']
        
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.assignment = context['assignment']
                instance.save() 
                
            messages.success(request, f"Successfully saved {len(instances)} marks for {context['target_class'].name}.")
            
            # Redirect back including the class_id to stay on the same roster
            return redirect(f"{reverse('academics:bulk_mark_entry', args=[assignment_id])}?class_id={context['target_class'].id}")
        
        return render(request, self.template_name, context)
        
class AllMarksListView(LoginRequiredMixin, ListView):
    model = Result
    template_name = 'academics/all_marks_list.html'
    context_object_name = 'results'

    def get_queryset(self):
        """Fetch results for the specific assignment identified in the URL."""
        # Retrieve the assignment; store it in self so get_context_data can use it
        self.assignment = get_object_or_404(CourseAssignment, id=self.kwargs['assignment_id'])
        
        # Return results filtered by this assignment, ordered by term and student name
        return Result.objects.filter(
            assignment=self.assignment
        ).order_by('term', 'student__user__last_name')

    def get_context_data(self, **kwargs):
        """Add the assignment object to the template context."""
        context = super().get_context_data(**kwargs)
        # Pass the assignment to the template so we can display the Subject/Class name
        context['assignment'] = self.assignment
        return context
    

# View to edit a single student's mark
class MarkUpdateView(LoginRequiredMixin, UpdateView):
    model = Result
    fields = ['term', 'score']
    template_name = 'academics/mark_form.html'
    
    def get_success_url(self):
        # Redirect back to the "View All" list for this specific assignment
        return reverse_lazy('academics:view_all_marks', kwargs={'assignment_id': self.object.assignment.id})

# View to delete a mark
class MarkDeleteView(LoginRequiredMixin, DeleteView):
    model = Result
    template_name = 'academics/mark_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('academics:view_all_marks', kwargs={'assignment_id': self.object.assignment.id})
    

class ExportMarksExcelView(LoginRequiredMixin, View):
    def get(self, request, assignment_id):
        # Fetch assignment and results
        assignment = get_object_or_404(CourseAssignment, id=assignment_id)
        results = Result.objects.filter(assignment=assignment).order_by('term', 'student__user__last_name')

        # Create workbook and sheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Class Marks"

        # Define Header Row (Clean version without Description)
        headers = ['Term', 'Student Name', 'Score (%)', 'Grade']
        ws.append(headers)

        # Style the header row (Optional: Bold headers)
        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)

        # Add Data Rows
        for res in results:
            ws.append([
                res.term,
                res.student.user.get_full_name(),
                res.score,  # Raw number for Excel calculations
                res.grade
            ])

        # Prepare the HTTP Response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        filename = f"{assignment.subject.name}_{assignment.class_level.name}_Marks.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
    

class StudentMarkListView(LoginRequiredMixin, ListView):
    model = Result
    template_name = 'academics/student_marks_view.html'
    context_object_name = 'my_results'

    def get_queryset(self):
        # Fetches all marks across all subjects for the logged-in student
        return Result.objects.filter(
            student__user=self.request.user
        ).order_by('-term', 'assignment__subject__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Identify the student profile
        # Assuming the Result model has a 'student' ForeignKey to StudentProfile
        first_result = self.get_queryset().first()
        
        if first_result:
            student = first_result.student
            # 2. Get the term to calculate for (defaulting to the latest in their results)
            term = self.request.GET.get('term', first_result.term)
            
            # 3. Calculate Aggregates and Division
            context['summary'] = ReportCalculator.get_summary(student, term)
            context['selected_term'] = term
        else:
            context['summary'] = {"aggregates": "N/A", "division": "N/A"}
            
        return context
    

class StudentSubjectMarkListView(LoginRequiredMixin, ListView):
    model = Result
    template_name = 'academics/student_marks_view.html'
    context_object_name = 'my_results'

    def get_queryset(self):
        # Filter marks by current student AND the specific subject from the URL
        return Result.objects.filter(
            student__user=self.request.user,
            assignment__subject_id=self.kwargs['subject_id']
        ).order_by('-term')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the subject name to the template for the heading
        from .models import Subject
        context['subject'] = get_object_or_404(Subject, id=self.kwargs['subject_id'])
        return context    
    



class CourseAssignmentListView(LoginRequiredMixin, ListView):
    model = CourseAssignment
    template_name = 'academics/assignment_list.html'
    context_object_name = 'assignments'
    
    def get_queryset(self):
        # Prefetching class_levels is necessary for ManyToMany relationships
        return CourseAssignment.objects.select_related('teacher', 'subject', 'academic_session').prefetch_related('class_levels').all()   


class CourseAssignmentDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = CourseAssignment
    template_name = 'academics/courseassignment_confirm_delete.html'
    success_url = reverse_lazy('academics:all_staff_load') # Redirects back to your directory list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete Assignment"
        return context    



class MaterialUploadView(CreateView):
    model = Material
    form_class = MaterialUploadForm
    template_name = 'academics/upload_material.html'
    
    def form_valid(self, form):
        # 1. Save the material instance (but don't commit yet to handle M2M)
        self.object = form.save(commit=False)
        self.object.save()
        
        # 2. Save the Many-to-Many relationships (The target classes)
        # This replaces the line causing your AttributeError
        form.save_m2m() 
        
        # 3. Create a safe success message
        # Instead of 'obj.target_class.name', we list all assigned classes
        assigned_classes = ", ".join([c.name for c in self.object.target_classes.all()])
        # messages.success(self.request, f"Uploaded for: {assigned_classes}") # Optional

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('academics:teacher_dashboard')    



class FullReportCardView(LoginRequiredMixin, DetailView):
    model = StudentProfile
    template_name = 'academics/student_marks'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        
        # Get term from URL parameters (e.g., ?term=TERM 1)
        term = self.request.GET.get('term', 'TERM 1')
        
        # Run the calculation logic
        summary_data = ReportCalculator.get_summary(student, term)
        
        context['results'] = student.results.filter(term=term).order_by('assignment__subject__name')
        context['summary'] = summary_data
        context['selected_term'] = term
        return context
    


class MarkEntryListView(LoginRequiredMixin, ListView):
    model = StudentProfile
    template_name = 'academics/mark_entry.html'
    context_object_name = 'students'

    def get_queryset(self):
        # Catch the class_name from the URL
        class_name = self.kwargs.get('class_name')
        
        # Filter students belonging to that class (e.g., 'senior two')
        return StudentProfile.objects.filter(
            current_class__name__iexact=class_name
        ).order_by('user__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_class'] = self.kwargs.get('class_name')
        return context    
    


class PromoteClassView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        from_class_id = request.POST.get('from_class')
        to_class_id = request.POST.get('to_class')

        if from_class_id == to_class_id:
            messages.error(request, "Source and Target classes cannot be the same.")
            return redirect('academics:class_list')

        # Update all active students in the source class
        updated_count = StudentProfile.objects.filter(
            current_class_id=from_class_id, 
            deleted_at__isnull=True
        ).update(current_class_id=to_class_id)

        messages.success(request, f"Successfully promoted {updated_count} students.")
        return redirect('academics:class_list')    