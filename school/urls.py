from django.urls import path
from school import views

urlpatterns = [
    # Authentication
    path('auth/login/', views.auth_login, name='auth-login'),
    path('auth/register/', views.auth_register, name='auth-register'),
    path('auth/logout/', views.auth_logout, name='auth-logout'),
    path('auth/me/', views.auth_me, name='auth-me'),
    path('auth/google/', views.auth_google, name='auth-google'),

    # Profile
    path('profile/me/', views.profile_me, name='profile-me'),
    path('profile/change-password/', views.profile_change_password, name='profile-change-password'),
    path('profile/<int:pk>/', views.profile_detail, name='profile-detail'),

    # Administrators (superadmin only)
    path('administrators/', views.administrators_list, name='administrators-list'),
    path('administrators/<int:pk>/', views.administrator_detail, name='administrator-detail'),
    path('administrators/<int:pk>/toggle/', views.admin_toggle_status, name='administrator-toggle'),
    path('administrators/<int:pk>/delete/', views.admin_delete, name='administrator-delete'),

    # Students (admin/superadmin)
    path('students/', views.students_list, name='students-list'),
    path('students/<int:pk>/', views.student_detail, name='student-detail'),

    # Users
    path('users/', views.users_list, name='users-list'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),

    # Groups
    path('groups/', views.groups_list, name='groups-list'),
    path('groups/<int:pk>/', views.group_detail, name='group-detail'),
    path('groups/<int:pk>/students/', views.group_students, name='group-students'),
    path('groups/<int:pk>/add_students/', views.group_add_students, name='group-add-students'),
    path('groups/<int:pk>/remove_student/', views.group_remove_student, name='group-remove-student'),

    # Subjects
    path('subjects/', views.subjects_list, name='subjects-list'),
    path('subjects/<int:pk>/', views.subject_detail, name='subject-detail'),

    # Lessons
    path('lessons/', views.lessons_list, name='lessons-list'),
    path('lessons/<int:pk>/', views.lesson_detail, name='lesson-detail'),

    # Tasks
    path('tasks/', views.tasks_list, name='tasks-list'),
    path('tasks/<int:pk>/', views.task_detail, name='task-detail'),
    path('tasks/<int:pk>/submissions/', views.task_submissions, name='task-submissions'),
    path('tasks/bulk-create/', views.tasks_bulk_create, name='tasks-bulk-create'),
    path('submissions/<int:pk>/grade/', views.grade_submission, name='grade-submission'),

    # Grades / Attendance
    path('grades/', views.grades_list, name='grades-list'),
    path('attendance/', views.attendance_list, name='attendance-list'),
    path('attendance/<int:pk>/', views.attendance_detail, name='attendance-detail'),
    path('attendance/lesson/<int:lesson_id>/', views.attendance_by_lesson, name='attendance-by-lesson'),
    path('attendance/bulk/', views.attendance_bulk_update, name='attendance-bulk'),
    path('attendance/my/', views.attendance_my, name='attendance-my'),

    # Invoices
    path('invoices/', views.invoices_list, name='invoices-list'),
    path('invoices/history/', views.invoices_history, name='invoices-history'),
    path('invoices/<int:pk>/remind/', views.invoice_remind, name='invoice-remind'),
    path('invoices/<int:pk>/pay/', views.invoice_pay, name='invoice-pay'),
    path('invoices/<int:pk>/submit-receipt/', views.invoice_submit_receipt, name='invoice-submit-receipt'),
    path('invoices/<int:pk>/receipts/<int:receipt_id>/review/', views.invoice_receipt_review, name='invoice-receipt-review'),

    # Admin
    path('admin/stats/', views.admin_stats, name='admin-stats'),
    path('admin/recent-activity/', views.admin_recent_activity, name='admin-recent-activity'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # News
    path('news/', views.news_list, name='news-list'),
    path('news/<int:pk>/', views.news_detail, name='news-detail'),
    path('news/<int:pk>/view/', views.news_view, name='news-view'),
    path('news/extra/', views.extra_news_list, name='extra-news-list'),
    path('news/extra/<int:pk>/', views.extra_news_detail, name='extra-news-detail'),

    # Chats
    path('chats/', views.chats_list, name='chats-list'),
    path('chats/<int:pk>/', views.chat_detail, name='chat-detail'),
    path('chats/<int:pk>/messages/', views.chat_messages, name='chat-messages'),

    # Polls
    path('polls/', views.polls_list, name='polls-list'),
    path('polls/<int:pk>/', views.poll_detail, name='poll-detail'),
    path('polls/<int:pk>/close/', views.poll_close, name='poll-close'),
    path('polls/<int:pk>/vote/', views.poll_vote, name='poll-vote'),

    # Courses
    path('courses/', views.courses_list, name='courses-list'),
    path('courses/<int:pk>/', views.course_detail, name='course-detail'),
    path('courses/<int:pk>/materials/', views.course_add_material, name='course-add-material'),
    path('courses/<int:course_pk>/materials/<int:material_pk>/', views.course_remove_material, name='course-remove-material'),
    path('courses/<int:pk>/tests/', views.course_add_test, name='course-add-test'),
    path('courses/<int:course_pk>/tests/<int:test_pk>/', views.course_remove_test, name='course-remove-test'),

    # Teams
    path('teams/', views.teams_list, name='teams-list'),
    path('teams/<int:pk>/', views.team_detail, name='team-detail'),
    path('teams/<int:pk>/members/', views.team_members, name='team-members'),
    path('teams/<int:pk>/add_members/', views.team_add_members, name='team-add-members'),
    path('teams/<int:pk>/remove_member/', views.team_remove_member, name='team-remove-member'),

    # Puzzles
    path('puzzles/', views.puzzles_list, name='puzzles-list'),
    path('puzzles/<int:pk>/', views.puzzle_detail, name='puzzle-detail'),
    path('puzzles/<int:pk>/answer/', views.puzzle_answer, name='puzzle-answer'),

    # Learning Materials
    path('materials/', views.learning_materials_list, name='learning-materials-list'),
    path('materials/<int:pk>/', views.learning_material_detail, name='learning-material-detail'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications-list'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification-read'),
]