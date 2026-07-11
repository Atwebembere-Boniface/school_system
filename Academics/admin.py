from django.contrib import admin
from .models import Subject, ClassLevel, StudentProfile, CourseAssignment

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # This adds columns to the list view so you can see the data
    list_display = ('registration_number', 'get_full_name', 'current_class', 'is_active')
    list_filter = ('current_class', 'deleted_at')
    search_fields = ('registration_number', 'user__username', 'user__first_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    # This creates a "Status" indicator in the admin list
    def is_active(self, obj):
        return obj.deleted_at is None
    is_active.boolean = True
    is_active.short_description = 'Active'

    # Custom Admin Actions
    actions = ['soft_delete_students', 'restore_students']

    def soft_delete_students(self, request, queryset):
        for student in queryset:
            student.soft_delete()
        self.message_user(request, "Selected students moved to Recycle Bin.")
    soft_delete_students.short_description = "Soft Delete selected students"

    def restore_students(self, request, queryset):
        for student in queryset:
            student.restore()
        self.message_user(request, "Selected students restored successfully.")
    restore_students.short_description = "Restore selected students"




@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'get_classes')
    # This creates the side-by-side selection boxes in the admin panel
    filter_horizontal = ('class_levels',) 

    def get_classes(self, obj):
        # This displays the list of classes in the admin table view
        return ", ".join([c.name for c in obj.class_levels.all()])
    
    get_classes.short_description = 'Assigned Classes'    