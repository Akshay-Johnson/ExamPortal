from django.contrib import admin
from .models import Exam, Question, Submission, ExamResult, StudentExam, StudentUser, TeacherUser, AdminUser
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# ✅ Student Group Filter
class StudentFilter(admin.SimpleListFilter):
    title = 'Student Group'
    parameter_name = 'student_group'

    def lookups(self, request, model_admin):
        return [('yes', 'Students')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(groups__name='Student')
        return queryset

# ✅ Teacher Group Filter
class TeacherFilter(admin.SimpleListFilter):
    title = 'Teacher Group'
    parameter_name = 'teacher_group'

    def lookups(self, request, model_admin):
        return [('yes', 'Teachers')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(groups__name='Teacher')
        return queryset

# ✅ Separate Student Admin
class StudentAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_active')
    search_fields = ('username', 'email')
    list_filter = (StudentFilter, 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(groups__name='Student')

# ✅ Separate Teacher Admin
class TeacherAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_active')
    search_fields = ('username', 'email')
    list_filter = (TeacherFilter, 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(groups__name='Teacher')

# ✅ Register Separate Admin Panels
admin.site.register(StudentUser, StudentAdmin)
admin.site.register(TeacherUser, TeacherAdmin)

# ✅ Exam Approval Filter
class ExamApprovalFilter(admin.SimpleListFilter):
    title = 'Approval Status'
    parameter_name = 'approval_status'

    def lookups(self, request, model_admin):
        return [
            ('pending', 'Pending Exams'),
            ('approved', 'Approved Exams'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(approval_status='pending')
        elif self.value() == 'approved':
            return queryset.filter(approval_status='approved')
        return queryset

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class ExamAdmin(admin.ModelAdmin):
    list_display = ['subject', 'created_by', 'approval_status', 'created_at']
    list_filter = ['approval_status', 'created_at']
    search_fields = ['subject', 'created_by__username']
    inlines = [QuestionInline]  
    actions = ['approve_selected', 'mark_as_pending']

    def approve_selected(self, request, queryset):
        queryset.update(approval_status='approved')
        self.message_user(request, "Selected exams have been approved.")

    def mark_as_pending(self, request, queryset):
        queryset.update(approval_status='pending')
        self.message_user(request, "Selected exams have been marked as pending.")

    approve_selected.short_description = "Approve selected exams"
    mark_as_pending.short_description = "Mark selected exams as pending"

admin.site.register(Exam, ExamAdmin)

# class QuestionAdmin(admin.ModelAdmin):
#     list_display = (
#         'text',  
#         'option_a_text', 'option_a_image',
#         'option_b_text', 'option_b_image',
#         'option_c_text', 'option_c_image',
#         'option_d_text', 'option_d_image',
#         'correct_answer'
#     )
#     list_filter = ('exam',)
#     search_fields = ['text', 'option_a_text', 'option_b_text', 'option_c_text', 'option_d_text']

# admin.site.register(Question, QuestionAdmin)

# # ✅ Student Exam Admin
# class StudentExamAdmin(admin.ModelAdmin):
#     list_display = ('student', 'exam', 'attempted_at', 'submitted_at')
#     list_filter = ('exam', 'submitted_at')
#     search_fields = ('student__username', 'exam__subject')
#     ordering = ('-submitted_at',)

# admin.site.register(StudentExam, StudentExamAdmin)

# ✅ Exam Result Admin
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'attempted_at')
    list_filter = ('exam', 'attempted_at')
    search_fields = ('student__username', 'exam__subject')
    ordering = ('-attempted_at',)

admin.site.register(ExamResult, ExamResultAdmin)

# ✅ Custom Admin Panel for Admin Users
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'date_joined')
    ordering = ('-date_joined',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=True)

admin.site.register(AdminUser, AdminUserAdmin)