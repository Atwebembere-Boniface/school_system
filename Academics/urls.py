from django.urls import path
from . import views

app_name = 'academics'  # Ensure this matches your namespace usage (academics:...)

urlpatterns = [
    # --- DASHBOARDS & CORE ---
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard_dispatch'),
    path('admin-portal/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('teacher-portal/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('student-portal/', views.StudentDashboardView.as_view(), name='student_dashboard'),

    # --- SUBJECTS & CLASSES ---
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_add'),
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_add'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/promote/', views.PromoteClassView.as_view(), name='promote_students'),
    path('class/<int:pk>/staff/', views.ClassStaffListView.as_view(), name='class_staff_list'),
    path('class/<int:pk>/students/', views.AssignedClassStudentListView.as_view(), name='assigned_student_list'),

    # --- STUDENT MANAGEMENT ---
    path('students/register/', views.StudentCreateView.as_view(), name='student_register'),
    path('all-students/', views.AllStudentsListView.as_view(), name='all_students_list'),
    path('student/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('student/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('student/<int:pk>/full-report/', views.FullReportCardView.as_view(), name='full_report_card'),
    path('student/<int:pk>/profile/', views.StudentDetailView.as_view(), name='student_profile'),

    # --- RECYCLE BIN ---
    path('recycle-bin/', views.RecycleBinListView.as_view(), name='recycle_bin'),
    path('student/<int:pk>/restore/', views.restore_student, name='student_restore'),
    path('student/<int:pk>/purge/', views.permanent_delete_student, name='student_perm_delete'),

    # --- STAFF LOADS & ASSIGNMENTS ---
    path('all-staff-loads/', views.AllStaffLoadListView.as_view(), name='all_staff_load'),
    path('assignments/', views.CourseAssignmentListView.as_view(), name='assignment_list'),
    path('assignments/add/', views.CourseAssignmentCreateView.as_view(), name='assign_course'),
    path('assignment/<int:pk>/edit/', views.CourseAssignmentUpdateView.as_view(), name='assignment_update'),
    path('assignment/<int:pk>/delete/', views.CourseAssignmentDeleteView.as_view(), name='assignment_delete'),

    # --- MATERIALS & RESOURCES ---
    path('my-materials/', views.TeacherMaterialListView.as_view(), name='teacher_materials'),
    path('material/upload/', views.MaterialUploadView.as_view(), name='upload_material'), # Combined duplicates
    path('material/<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='delete_material'),
    path('material/<int:pk>/download/', views.track_material_download, name='track_download'),
    path('subject/<int:subject_id>/resources/', views.SubjectResourceListView.as_view(), name='subject_resources'),

    # --- TIMETABLE ---
    path('timetable/upload/', views.TimetableUploadView.as_view(), name='timetable_upload'),
    path('timetable/<int:pk>/delete/', views.TimetableDeleteView.as_view(), name='timetable_delete'),
    path('timetable/<int:pk>/download/', views.track_timetable_download, name='track_timetable_download'),

    # --- MARKS & RESULTS ---
    path('my-marks/', views.StudentMarkListView.as_view(), name='student_marks'),
    path('my-marks/subject/<int:subject_id>/', views.StudentSubjectMarkListView.as_view(), name='student_subject_marks'),
    path('marks/entry/<int:assignment_id>/', views.MarkEntryView.as_view(), name='mark_entry'),
    path('marks/bulk-entry/<int:assignment_id>/', views.BulkMarkEntryView.as_view(), name='bulk_mark_entry'),
    path('marks/view-all/<int:assignment_id>/', views.AllMarksListView.as_view(), name='view_all_marks'),
    path('marks/edit/<int:pk>/', views.MarkUpdateView.as_view(), name='edit_mark'),
    path('marks/delete/<int:pk>/', views.MarkDeleteView.as_view(), name='delete_mark'),
    path('marks/export-excel/<int:assignment_id>/', views.ExportMarksExcelView.as_view(), name='export_excel'),
    path('enter-marks/<str:class_name>/', views.MarkEntryListView.as_view(), name='enter_marks'),
]