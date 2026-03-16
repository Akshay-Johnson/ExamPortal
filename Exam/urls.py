from django.contrib import admin
from django.urls import path
from . import views  # Import all views at once
from django.conf import settings
from django.conf.urls.static import static
from .views import save_recording


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    
    # Authentication
    path('adminlogin/', views.adminlogin, name='adminlogin'),
    path('studentlogin', views.studentlogin, name='studentlogin'),
    path('studentregister', views.studentregister, name='studentregister'),
    path('teacherlogin', views.teacherlogin, name='teacherlogin'),
    path('teacherregister', views.teacherregister, name='teacherregister'),
    path('logout/', views.user_logout, name='user_logout'),
    path('clear-popup-message/', views.clear_popup_message, name='clear_popup_message'),
    
    # Dashboards
    path('studentdashboard/', views.studentdashboard, name='studentdashboard'),
    path('teacherdashboard/', views.teacherdashboard, name='teacherdashboard'),
    path('admindashboard/', views.admindashboard, name='admindashboard'),
    path('adminlogout/', views.adminlogout, name='adminlogout'),

    # Teacher Management
    path('teacherapproval', views.teacherapproval, name='teacherapproval'),
    path('approve_teacher/<int:teacher_id>/', views.approve_teacher, name='approve_teacher'),
    path('reject_teacher/<int:teacher_id>/', views.reject_teacher, name='reject_teacher'),
    path('teacher_pending/', views.teacher_pending, name='teacher_pending'),
    
    # Student & Teacher Management
    path('manage/student/<int:id>/', views.manage_student, name='manage_student'),
    path('delete/student/<int:id>/', views.delete_student, name='delete_student'),
    path('manage/teacher/<int:id>/', views.manage_teacher, name='manage_teacher'),
    path('delete/teacher/<int:id>/', views.delete_teacher, name='delete_teacher'),
    path('manage-users/', views.manage_users, name='manage_users'),
    # path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'), 

    # Exam Management
    path("create_exam/", views.create_exam, name="create_exam"),
    path("view_created_exams/", views.view_created_exams, name="view_created_exams"),
    path("available_exam/", views.available_exam, name="available_exam"),
    path('manage_exams/', views.manage_exams, name='manage_exams'),
    #path('exams/delete/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path("remove-exam/<int:exam_id>/", views.remove_exam, name="remove_exam"),
    path("confirm-remove-exam/<int:exam_id>/", views.confirm_remove_exam, name="confirm_remove_exam"),
    path('exam/update/<int:exam_id>/', views.update_exam, name='update_exam'),
    path('start-exam/<int:exam_id>/', views.start_exam, name='start_exam'),
    path('exam/<int:exam_id>/take/', views.take_exam, name='take_exam'),
    path('exam/completed/', views.exam_completed, name='exam_completed'),
    path('submit_exam/<int:exam_id>/', views.submit_exam, name='submit_exam'),
    path('my-results/', views.my_results, name='my_results'),
    path('save-recording/', save_recording, name='save_recording'),
    # path('upload-recording/<int:exam_id>/', views.upload_recording, name='upload_recording'),
    path("upload-recording/<int:exam_id>/", views.upload_recording, name="upload_recording"),
    path('exam-results/', views.exam_results, name='exam_results'),
    path('download-exam-report/<int:exam_id>/', views.download_exam_report, name='download_exam_report'),
    path('admin/exam/approve/<int:exam_id>/', views.approve_exam, name='approve_exam'),
    path('admin/exam/reject/<int:exam_id>/', views.reject_exam, name='reject_exam'),
    path('admin/pending-exams/', views.admin_pending_exams, name='admin_pending_exams'),
    
    
    # path('exam/view/<int:exam_id>/', views.view_exam_teacher, name='view_exam'),
    path('exam/view/<int:exam_id>/', views.view_exam_teacher, name='view_exam_teacher'),



    path('admin-dashboard/exam-approval/', views.exam_approval, name='exam_approval'),
    
    path('admin-dashboard/approve-exam/<int:exam_id>/', views.approve_exam, name='approve_exam'),
    path('admin-dashboard/reject-exam/<int:exam_id>/', views.reject_exam, name='reject_exam'),


    

    # Profiles
    path('teacher/profile/', views.teacher_profile, name='teacher_profile'),
    path('teacher/edit-profile/', views.edit_teacher_profile, name='edit_teacher_profile'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('student/edit-profile/', views.edit_student_profile, name='edit_student_profile'),
    path('student/update-profile/', views.update_student_profile, name='update_student_profile'),



    path("remove-exam/<int:exam_id>/", views.remove_exam, name="remove_exam"),
    path("confirm-remove-exam/<int:exam_id>/", views.confirm_remove_exam, name="confirm_remove_exam"),
    # path('record-malpractice/', views.record_malpractice, name='record_malpractice'),
    path("record_malpractice/", views.record_malpractice, name="record_malpractice"),
    path("malpractice_count/<int:exam_id>/", views.get_malpractice_count, name="malpractice_count"),
    
    path("send-result-email/", views.send_result_email, name="send_result_email"),
    path('send-exam-report/', views.send_exam_report_email_to_teacher, name='send_exam_report_email_to_teacher')



]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    