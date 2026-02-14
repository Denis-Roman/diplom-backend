from django.urls import path
from school.views import (
    auth_login, auth_register, auth_logout, auth_me,
    students_list, student_detail,
    groups_list, group_detail, group_students,
    subjects_list, subject_detail,
    lessons_list, lesson_detail, lesson_grades,
    tasks_list, task_submissions, grade_submission,
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

    # Students
    path('students/', students_list, name='students-list'),
    path('students/<int:pk>/', student_detail, name='student-detail'),

    # Groups
    path('groups/', groups_list, name='groups-list'),
    path('groups/<int:pk>/', group_detail, name='group-detail'),
    path('groups/<int:pk>/students/', group_students, name='group-students'),

    # Subjects
    path('subjects/', subjects_list, name='subjects-list'),
    path('subjects/<int:pk>/', subject_detail, name='subject-detail'),

    # Lessons
    path('lessons/', lessons_list, name='lessons-list'),
    path('lessons/<int:pk>/', lesson_detail, name='lesson-detail'),
    path('lessons/<int:pk>/grades/', lesson_grades, name='lesson-grades'),

    # Tasks
    path('tasks/', tasks_list, name='tasks-list'),
    path('tasks/<int:pk>/submissions/', task_submissions, name='task-submissions'),
    path('submissions/<int:pk>/grade/', grade_submission, name='grade-submission'),

    # Grades
    path('grades/', grades_list, name='grades-list'),

    # Attendance
    path('attendance/', attendance_list, name='attendance-list'),

    # Invoices
    path('invoices/', invoices_list, name='invoices-list'),
    path('invoices/history/', invoices_history, name='invoices-history'),

    # Admin
    path('admin/stats/', admin_stats, name='admin-stats'),
    path('administrators/', administrators_list, name='administrators-list'),
    path('administrators/<int:pk>/', administrator_detail, name='administrator-detail'),

    # Leaderboard
    path('leaderboard/', leaderboard, name='leaderboard'),

    # News
    path('news/extra/', extra_news_list, name='extra-news-list'),
    path('news/extra/<int:pk>/', extra_news_detail, name='extra-news-detail'),
    path('news/', news_list, name='news-list'),
    path('news/<int:pk>/', news_detail, name='news-detail'),

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
    path('courses/<int:pk>/', course_detail, name='course-detail'),

    # Teams
    path('teams/', teams_list, name='teams-list'),
    path('teams/<int:pk>/', team_detail, name='team-detail'),
    path('teams/<int:pk>/members/', team_members, name='team-members'),

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
]