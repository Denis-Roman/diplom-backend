from django.contrib import admin
from school.models import (
    User, Group, GroupStudent, Subject, Lesson, LessonGrade,
    Attendance, Task, TaskAttachment, TaskSubmission, SubmissionFile,
    Invoice, Notification, News, ExtraNews, StudentPoint, Team, TeamMember,
    Chat, ChatParticipant, ChatMessage, ChatMessageAttachment,
    Poll, PollOption, PollVote,
    Course, CourseLesson, CourseLessonQuestion,
    Puzzle, LearningMaterial, LearningMaterialAttachment,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'role', 'status', 'created_at']
    list_filter = ['role', 'status']
    search_fields = ['name', 'email']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'color', 'created_at']


@admin.register(GroupStudent)
class GroupStudentAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'student', 'joined_at']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'short_name', 'color']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'subject', 'group', 'scheduled_date', 'start_time', 'status']
    list_filter = ['status', 'scheduled_date']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'type', 'group', 'subject', 'due_date', 'max_grade']
    list_filter = ['type']


@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'student', 'status', 'grade', 'submitted_at']
    list_filter = ['status']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'amount', 'paid_amount', 'status', 'due_date']
    list_filter = ['status']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'lesson', 'student', 'status']
    list_filter = ['status']


admin.site.register(LessonGrade)
admin.site.register(TaskAttachment)
admin.site.register(SubmissionFile)
admin.site.register(Notification)
admin.site.register(News)
admin.site.register(ExtraNews)
admin.site.register(StudentPoint)
admin.site.register(Team)
admin.site.register(TeamMember)
admin.site.register(Chat)
admin.site.register(ChatParticipant)
admin.site.register(ChatMessage)
admin.site.register(ChatMessageAttachment)
admin.site.register(Poll)
admin.site.register(PollOption)
admin.site.register(PollVote)
admin.site.register(Course)
admin.site.register(CourseLesson)
admin.site.register(CourseLessonQuestion)
admin.site.register(Puzzle)
admin.site.register(LearningMaterial)
admin.site.register(LearningMaterialAttachment)
