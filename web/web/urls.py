from django.urls import path
from django.contrib import admin
from webapp.views import icon_view, admin_calendar, change_password, create_event, create_group, delete_event, edit_admin_profile, faculty_change_password, get_events, home, signin, signout, forgot_password, reset_password, student_calendar, student_change_password, student_home, faculty_home, admin_home, update_event
from webapp.admin_views import   admin_dashboard, delete_faculty, delete_student, download_user_template,add_department, edit_faculty, list_faculty,update_department,delete_department, add_by_file, download_faculty_template, bulk_upload_faculty, download_faculty_formate, download_student_template, download_student_format, bulk_upload_student, manage_schemes, update_scheme, toggle_scheme_status, delete_scheme , manage_enrollments, update_enrollment, delete_enrollment, manage_courses_and_schemes,export_courses_csv,download_course_template,delete_course,update_course,update_scheme_mapping,view_course_enrollments, enrollment_detail, list_students, edit_student
from webapp.faculty_views import course_students, fac_course, faculty_list_students,faculty_profile, get_student_results, save_student_results,student_detail,faculty_dashboard,post_announcement,course_actions, confirm_attendance,attendance,download_attendance_template,upload_attendance_csv, results, documentation_view,download_results_template, upload_results_csv
from webapp.Student_views import profile_details, store_course_results, store_semester_results, student_attendance_view, student_dashboard, student_enrollments, student_results, update_all_results, view_announcements
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    # Admin URLs
    path('admin/', admin.site.urls),
    path('', signin, name='signin'),
    path('home/', home, name='home'),
    path('admin-home/', admin_dashboard, name='admin_home'),
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('student-home/', student_dashboard, name='student_home'),
    path('faculty-home/', faculty_home, name='faculty_home'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
    path('forgot-password/', forgot_password, name='forgot_password'), # for password reset
    path('reset-password/<str:token>/', reset_password, name='reset_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'), 
    path('groups/create/', create_group, name='create_group'),
    # Custom User URLs
    path('add-by-file/', add_by_file, name='add_by_file'),
    path('download-user-template/', download_user_template, name='download_user_template'),# for downloading the user template
    # Department URLs
    path('add-department/', add_department, name='add_department'),  # for adding department
    path('update-department/<int:department_id>/', update_department, name='update_department'),
    path('delete-department/<int:department_id>/', delete_department, name='delete_department'),
    # Faculty bulk upload URLs
    path('faculty/download-template/', download_faculty_template, name='download_faculty_template'),
    path('faculty/bulk-upload/', bulk_upload_faculty, name='bulk_upload_faculty'),
    path('download-faculty_formate/', download_faculty_formate, name='download_faculty_formate'),
    # Faculty Management URLs
    path('faculty-management/', list_faculty, name='list_faculty'),
    path('edit-faculty/<int:faculty_id>/', edit_faculty, name='edit_faculty'),
    path('delete-faculty/<int:faculty_id>/', delete_faculty, name='delete_faculty'),
    # Student bulk upload URLs
    path('student/download-template/', download_student_template, name='download_student_template'),
    path('student/download-format/', download_student_format, name='download_student_format'),
    path('student/bulk-upload/', bulk_upload_student, name='bulk_upload_student'),
    #student URLs
    path('students/', list_students, name='list_students'),
    path('edit-student/<int:student_id>/', edit_student, name='edit_student'),
    path('delete-student/<int:student_id>/', delete_student, name='delete_student'),
    # Scheme URLs
    path('schemes/', manage_schemes, name='manage_schemes'),
    path('schemes/update/<int:scheme_id>/', update_scheme, name='update_scheme'),
    path('schemes/toggle-status/<int:scheme_id>/', toggle_scheme_status, name='toggle_scheme_status'),
    path('schemes/delete/<int:scheme_id>/', delete_scheme, name='delete_scheme'),
    #course URLs
    path('courses/', manage_courses_and_schemes, name='manage_courses_and_schemes'),
    path('scheme-mapping/update/<int:mapping_id>/', update_scheme_mapping, name='update_scheme_mapping'),
    path('courses/export/', export_courses_csv, name='export_courses_csv'),
    path('download-course-template/', download_course_template, name='download_course_template'),
    path('course/update/<int:course_id>/', update_course, name='update_course'),
    path('course/delete/<int:course_id>/', delete_course, name='delete_course'),
    # Enrollment URLs
    path('enrollments/', manage_enrollments, name='manage_enrollments'),
    path('course-enrollments/', view_course_enrollments, name='view_course_enrollments'),
    path('enrollment-detail/<int:course_id>/<int:semester>/<int:scheme_id>/', enrollment_detail, name='enrollment_detail'),
    path('enrollments/update/<int:enrollment_id>/', update_enrollment, name='update_enrollment'),
    path('<int:course_id>/<int:semester>/<int:scheme_id>/', delete_enrollment, name='delete_enrollment'),
    # Admin Profile URLs
    path('profile/edit/', edit_admin_profile, name='edit_admin_profile'),
    #Change Password URL
    path('change-password/', change_password, name='change_password'),
    path('students/change-password/', student_change_password, name='student_change_password'),
    path('faculty/change-password/', faculty_change_password, name='faculty_change_password'),
    #Event Calendar(Admin and Student)
    path('admin-calendar/', admin_calendar, name='admin_calendar'),
    path('calendar/', student_calendar, name='student_calendar'),
    
    # API URLs
    path('api/events/', get_events, name='get_events'),
    path('api/events/create/', create_event, name='create_event'),
    path('api/events/<int:event_id>/', update_event, name='update_event'),
    path('api/events/<int:event_id>/delete/', delete_event, name='delete_event'),
    
    #Faculty Routes
    path('attendance/<str:course_name>/download_template/', download_attendance_template, name='download_attendance_template'),
    path('attendance/<str:course_name>/upload/', upload_attendance_csv, name='upload_attendance_csv'),
    path('faculty/', faculty_dashboard, name='faculty_home'),
    path('fac_course/', fac_course, name='fac_course'),
    path('attendance/<str:course_name>/', attendance, name='attendance'),
    path('download_attendance/<str:course_name>/', download_attendance_template, name='download_attendance_template'),
    path('upload_attendance/<str:course_name>/', upload_attendance_csv, name='upload_attendance_csv'),
    path('attendance/<str:course_name>/confirm/', confirm_attendance, name='confirm_attendance'),
    path('results/<str:course_name>/', results, name='results'),
    path('results/<str:course_name>/download_template/', download_results_template, name='download_results_template'),
    path('results/<str:course_name>/upload/', upload_results_csv, name='upload_results_csv'),
    path('post-announcement/', post_announcement, name='post_announcement'),
    path('course-actions/<str:action_type>/', course_actions, name='course_actions'),
    path('student/<int:student_id>/', student_detail, name='student_detail'),
    path('profile/', faculty_profile, name='faculty_profile'),
    path('dashboard/', faculty_dashboard, name='faculty_dashboard'),
    path('documentation/', documentation_view, name='documentation'),
    path('faculty/list/students/', faculty_list_students, name='faculty_list_students'),
    path('course_students/<int:course_id>/', course_students, name='course_students'),
    path('api/get_student_results/<int:course_id>/<int:student_id>/', get_student_results, name='get_student_results'),
    path('save_student_results/', save_student_results, name='save_student_results'),
    #Student Routes
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('profile-details/', profile_details, name='profile_details'),
    path('student/results', student_results, name='student_results'),
    path('student/courses/', student_enrollments, name='student_enrollments'),
    path('attendance/', student_attendance_view, name='student_attendance'),
    path('store-course-results/', store_course_results, name='store_course_results'),
    path('store-semester-results/', store_semester_results, name='store_semester_results'),
    path('update-all-results/', update_all_results, name='update_all_results'),
    path('announcements/', view_announcements, name='student_announcements'),

    path('icon/', icon_view, name='icon'),  
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)