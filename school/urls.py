from django.urls import path
from . import views
from .views import ( admin_toggle_status, admin_delete )
from school.views import (
    attendance_detail, attendance_by_lesson,
    auth_login, auth_register, auth_logout, auth_me,
    students_list, student_detail,
    users_list, user_detail,
    groups_list, group_detail, group_students,
    subjects_list, subject_detail,
    lessons_list, lesson_detail, lesson_grades,
    tasks_list, task_detail, task_submissions, grade_submission,
    grades_list, attendance_list,
    invoices_list, invoices_history,
    admin_stats, leaderboard,
    extra_news_list, extra_news_detail,
    news_list, news_detail,
    chats_list, chat_detail, chat_messages,
    polls_list, poll_detail, poll_vote,
    courses_list, course_detail,
    teams_list, team_detail, team_members,
    puzzles_list, puzzle_detail, puzzle_answer,
    learning_materials_list, learning_material_detail,
    administrators_list, administrator_detail,
    notifications_list, notification_read,
)

urlpatterns = [
    # Authentication
    path('auth/login/', auth_login, name='auth-login'),
    path('auth/register/', auth_register, name='auth-register'),
    path('auth/logout/', auth_logout, name='auth-logout'),
    path('auth/me/', auth_me, name='auth-me'),
    path('administrators/', administrators_list),
    path('administrators/<int:pk>/toggle/', admin_toggle_status),
    path('administrators/<int:pk>/', admin_delete),
    path('auth/login/', auth_login),
    path('api/auth/login/', views.auth_login),
    path('api/auth/register/', views.auth_register),
    path('api/administrators/', views.administrators_list, name='administrators_list'),
    path('api/administrators/<int:pk>/', views.administrator_detail, name='administrator_detail'),
    path('api/administrators/<int:pk>/toggle/', views.admin_toggle_status, name='admin_toggle_status'),
    path('api/administrators/<int:pk>/delete/', views.admin_delete, name='admin_delete'),

    # Students
    path('students/', students_list, name='students-list'),
    path('students/<int:pk>/', student_detail, name='student-detail'),
    path('api/students/', views.students_list),
    path('api/students/<int:pk>/', views.student_detail),

    # Groups
    path('groups/', groups_list, name='groups-list'),
    path('groups/<int:pk>/', group_detail, name='group-detail'),
    path('groups/<int:pk>/students/', group_students, name='group-students'),
    path('groups/<int:pk>/add_students/',views.group_add_students,name='group_add_students'),
    path('groups/<int:pk>/remove_student/', views.group_remove_student, name='group_remove_student'),

# Users
    path('users/', users_list, name='users-list'),
    path('users/<int:pk>/', user_detail, name='user-detail'),

    # Subjects
    path('subjects/', subjects_list, name='subjects-list'),
    path('subjects/<int:pk>/', subject_detail, name='subject-detail'),

    # Lessons
    path('lessons/', lessons_list, name='lessons-list'),
    path('lessons/<int:pk>/', lesson_detail, name='lesson-detail'),
    path('lessons/<int:pk>/grades/', lesson_grades, name='lesson-grades'),

    # Tasks
    path('tasks/', tasks_list, name='tasks-list'),
    path('tasks/<int:pk>/', task_detail, name='task-detail'),
    path('tasks/<int:pk>/', views.task_detail, name='task-detail'),
    path('tasks/<int:pk>/submissions/', task_submissions, name='task-submissions'),
    path('submissions/<int:pk>/grade/', grade_submission, name='grade-submission'),
    path('tasks/bulk-create/', views.tasks_bulk_create, name='tasks-bulk-create'),

    # Grades
    path('grades/', grades_list, name='grades-list'),

    # Attendance
    path('attendance/', attendance_list, name='attendance-list'),
    path('attendance/<int:pk>/', attendance_detail, name='attendance-detail'),
    path('attendance/lesson/<int:lesson_id>/', attendance_by_lesson, name='attendance-by-lesson'),

    # Invoices
    path('invoices/', invoices_list, name='invoices-list'),
    path('invoices/history/', invoices_history, name='invoices-history'),

    # Admin
    path('api/administrators/<int:pk>/', views.admin_delete),
    path('api/administrators/<int:pk>/toggle/', views.admin_toggle_status),
    path('api/administrators/', views.administrators_list),
    path('admin/stats/', admin_stats, name='admin-stats'),
    path('administrators/', administrators_list, name='administrators-list'),
    path('administrators/<int:pk>/', administrator_detail, name='administrator-detail'),
    path('administrators/', administrators_list, name='administrators'),
    path('administrators/<int:pk>/', administrator_detail, name='administrator_detail'),
    path('administrators/<int:pk>/toggle/', admin_toggle_status, name='admin_toggle_status'),
    path('administrators/<int:pk>/delete/', admin_delete, name='admin_delete'),  # опціонально

    # Leaderboard
    path('leaderboard/', leaderboard, name='leaderboard'),

    # News
    path('news/extra/', extra_news_list, name='extra-news-list'),
    path('news/extra/<int:pk>/', extra_news_detail, name='extra-news-detail'),
    path('news/', news_list, name='news-list'),
    path('news/<int:pk>/', news_detail, name='news-detail'),
    path('api/news/', views.news_list),
    path('api/news/<int:pk>/', views.news_detail),
    path('api/news/<int:pk>/', views.news_update),

    # Chats
    path('chats/', chats_list, name='chats-list'),
    path('chats/<int:pk>/', chat_detail, name='chat-detail'),
    path('chats/<int:pk>/messages/', chat_messages, name='chat-messages'),

    # Polls
    path('polls/', polls_list, name='polls-list'),
    path('polls/<int:pk>/', poll_detail, name='poll-detail'),
    path('polls/<int:pk>/vote/', poll_vote, name='poll-vote'),


    # Courses
    path('courses/', courses_list, name='courses-list'),
    path('courses/<int:pk>/', course_detail, name='course-detail'),  # ← МАЄ БУТИ СЛЕШ!
    path('courses/<int:pk>/materials/', views.course_add_material, name='course-add-material'),
    path('courses/<int:course_pk>/materials/<int:material_pk>/', views.course_remove_material,name='course-remove-material'),
    path('courses/<int:pk>/tests/', views.course_add_test, name='course-add-test'),
    path('courses/<int:course_pk>/tests/<int:test_pk>/', views.course_remove_test, name='course-remove-test'),

    # Teams
    path('teams/', teams_list, name='teams-list'),
    path('teams/<int:pk>/', team_detail, name='team-detail'),
    path('teams/<int:pk>/members/', team_members, name='team-members'),
    path('teams/<int:pk>/add_members/', views.team_add_members, name='team-add-members'),
    path('teams/<int:pk>/remove_member/', views.team_remove_member, name='team-remove-member'),


    # Puzzles
    path('puzzles/', puzzles_list, name='puzzles-list'),
    path('puzzles/<int:pk>/', puzzle_detail, name='puzzle-detail'),
    path('puzzles/<int:pk>/answer/', puzzle_answer, name='puzzle-answer'),

    # Learning Materials
    path('materials/', learning_materials_list, name='learning-materials-list'),
    path('materials/<int:pk>/', learning_material_detail, name='learning-material-detail'),

    # Notifications
    path('notifications/', notifications_list, name='notifications-list'),
    path('notifications/<int:pk>/read/', notification_read, name='notification-read'),

    #Attendance
    path('api/attendance/', views.attendance_by_lesson, name='attendance_by_lesson'),
    path('api/attendance/bulk/', views.attendance_bulk_update, name='attendance_bulk_update'),
]