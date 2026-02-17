from django.db import models
from django.utils import timezone



class User(models.Model):
    ROLE_CHOICES = [('superadmin', 'SuperAdmin'), ('admin', 'Admin'), ('student', 'Student')]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    phone = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True, db_column='avatarUrl')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    registered_at = models.DateField(default=timezone.now, db_column='registeredAt')
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)

    class Meta:
        db_table = 'Users'

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#7c3aed')
    schedule = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Groups'

    def __str__(self):
        return self.name


class GroupStudent(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, db_column='groupId', related_name='memberships')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId', related_name='group_memberships')
    joined_at = models.DateTimeField(auto_now_add=True, db_column='joinedAt')

    class Meta:
        db_table = 'GroupStudents'
        unique_together = ('group', 'student')


class Subject(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=10, db_column='shortName')
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#7c3aed')
    image_url = models.TextField(blank=True, null=True, db_column='imageUrl')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Subjects'

    def __str__(self):
        return self.name


class Lesson(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField(db_column='startTime')
    end_time = models.TimeField(db_column='endTime')
    meeting_link = models.URLField(max_length=500, blank=True, null=True,
                                   db_column='meetingLink')  # ← ДОДАЙТЕ ЦЕЙ РЯДОК
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, db_column='subjectId')
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'Lessons'

    def __str__(self):
        return f"{self.title} - {self.date}"

class LessonGrade(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, db_column='lessonId', related_name='grades')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId')
    grade = models.IntegerField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    graded_at = models.DateTimeField(auto_now_add=True, db_column='gradedAt')

    class Meta:
        db_table = 'LessonGrades'
        unique_together = ('lesson', 'student')

class Attendance(models.Model):
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Присутній'),
        ('late', 'Запізнився'),
        ('absent', 'Відсутній'),
    ], default='present')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lesson', 'user')

    def __str__(self):
        return f"{self.user.name} - {self.lesson.title} - {self.status}"


class Task(models.Model):
    TYPE_CHOICES = [
        ('homework', 'Homework'), ('project', 'Project'), ('test', 'Test'),
        ('practice', 'Practice'), ('classwork', 'Classwork'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subjectId')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='homework')
    due_date = models.DateTimeField(null=True, blank=True, db_column='dueDate')
    max_grade = models.IntegerField(default=100, db_column='maxGrade')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Tasks'

    def __str__(self):
        return self.title


class TaskAttachment(models.Model):
    TYPE_CHOICES = [
        ('document', 'Document'), ('video', 'Video'),
        ('link', 'Link'), ('file', 'File'), ('image', 'Image'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, db_column='taskId', related_name='attachments')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255)
    url = models.TextField(blank=True, null=True)
    file_size = models.CharField(max_length=50, blank=True, null=True, db_column='fileSize')

    class Meta:
        db_table = 'TaskAttachments'


class TaskSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('submitted', 'Submitted'), ('graded', 'Graded'),
        ('overdue', 'Overdue'), ('returned', 'Returned'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, db_column='taskId', related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId')
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    grade = models.IntegerField(null=True, blank=True)
    teacher_comment = models.TextField(blank=True, null=True, db_column='teacherComment')
    submitted_at = models.DateTimeField(null=True, blank=True, db_column='submittedAt')
    graded_at = models.DateTimeField(null=True, blank=True, db_column='gradedAt')

    class Meta:
        db_table = 'TaskSubmissions'
        unique_together = ('task', 'student')


class SubmissionFile(models.Model):
    submission = models.ForeignKey(TaskSubmission, on_delete=models.CASCADE, db_column='submissionId', related_name='files')
    file_name = models.CharField(max_length=255, db_column='fileName')
    file_url = models.TextField(db_column='fileUrl')
    file_size = models.CharField(max_length=50, blank=True, null=True, db_column='fileSize')
    file_type = models.CharField(max_length=20, default='file', db_column='fileType')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_column='uploadedAt')

    class Meta:
        db_table = 'SubmissionFiles'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('partial', 'Partial'),
        ('paid', 'Paid'), ('overdue', 'Overdue'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId', related_name='invoices')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='paidAmount')
    installments = models.IntegerField(default=1)
    current_installment = models.IntegerField(default=1, db_column='currentInstallment')
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True, db_column='dueDate')
    paid_at = models.DateTimeField(null=True, blank=True, db_column='paidAt')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Invoices'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', related_name='notifications')
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False, db_column='isRead')
    link = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Notifications'


class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image_url = models.TextField(blank=True, null=True, db_column='imageUrl')  # для фото/cover
    video_url = models.TextField(blank=True, null=True, db_column='videoUrl')  # для відео
    link = models.TextField(blank=True, null=True)  # для стороннього посилання
    category = models.CharField(max_length=100, blank=True, null=True)
    is_published = models.BooleanField(default=False, db_column='isPublished')
    published_at = models.DateTimeField(null=True, blank=True, db_column='publishedAt')
    image_file = models.ImageField(upload_to='news_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    views_count = models.IntegerField(default=0) # нове поле

    class Meta:
        db_table = 'News'


class ExtraNews(models.Model):
    MEDIA_TYPE_CHOICES = [('image', 'Image'), ('video', 'Video')]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, null=True, blank=True, db_column='mediaType')
    media_url = models.TextField(blank=True, null=True, db_column='mediaUrl')
    is_active = models.BooleanField(default=True, db_column='isActive')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'ExtraNews'


class StudentPoint(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId', related_name='points')
    points = models.IntegerField()
    source_type = models.CharField(max_length=50, db_column='sourceType')
    source_id = models.IntegerField(null=True, blank=True, db_column='sourceId')
    description = models.TextField(blank=True, null=True)
    earned_at = models.DateTimeField(auto_now_add=True, db_column='earnedAt')

    class Meta:
        db_table = 'StudentPoints'


class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#FF9A00')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    total_points = models.IntegerField(default=0, db_column='totalPoints')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Teams'

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='teamId', related_name='members')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId')
    joined_at = models.DateTimeField(auto_now_add=True, db_column='joinedAt')

    class Meta:
        db_table = 'TeamMembers'
        unique_together = ('team', 'student')


# ─── CHAT ──────────────────────────────────────────────

class Chat(models.Model):
    TYPE_CHOICES = [('private', 'Private'), ('group', 'Group')]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='private')
    name = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='createdBy', related_name='created_chats')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Chats'

    def __str__(self):
        return self.name or f"Chat #{self.id}"


class ChatParticipant(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, db_column='chatId', related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', related_name='chat_participations')
    joined_at = models.DateTimeField(auto_now_add=True, db_column='joinedAt')

    class Meta:
        db_table = 'ChatParticipants'
        unique_together = ('chat', 'user')


class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, db_column='chatId', related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, db_column='senderId', related_name='sent_messages')
    content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'ChatMessages'
        ordering = ['created_at']


class ChatMessageAttachment(models.Model):
    TYPE_CHOICES = [('image', 'Image'), ('video', 'Video'), ('file', 'File')]

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, db_column='messageId', related_name='attachments')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='file')
    name = models.CharField(max_length=255)
    url = models.TextField()
    size = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'ChatMessageAttachments'


# ─── POLLS ──────────────────────────────────────────────

class Poll(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('closed', 'Closed'), ('draft', 'Draft')]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_type = models.CharField(max_length=20, default='all', db_column='targetType')
    target_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_column='targetGroupId')
    is_anonymous = models.BooleanField(default=False, db_column='isAnonymous')
    is_multiple_choice = models.BooleanField(default=False, db_column='isMultipleChoice')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    ends_at = models.DateField(db_column='endsAt')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'Polls'

    def __str__(self):
        return self.title


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, db_column='pollId', related_name='options')
    text = models.CharField(max_length=255)

    class Meta:
        db_table = 'PollOptions'


class PollVote(models.Model):
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, db_column='optionId', related_name='votes')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId')
    voted_at = models.DateTimeField(auto_now_add=True, db_column='votedAt')

    class Meta:
        db_table = 'PollVotes'
        unique_together = ('option', 'student')


# ─── COURSES (Learning) ──────────────────────────────────

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subjectId')
    thumbnail = models.URLField(blank=True, null=True)
    is_published = models.BooleanField(default=False, db_column='isPublished')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'Courses'

    def __str__(self):
        return self.title


class CourseMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ('video', 'Video'),
        ('youtube', 'YouTube'),
        ('document', 'Document'),
        ('link', 'Link'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials', db_column='courseId')
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES)
    url = models.URLField()
    order = models.IntegerField(default=0)
    duration = models.IntegerField(null=True, blank=True)  # в секундах
    is_required = models.BooleanField(default=True, db_column='isRequired')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'CourseMaterials'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseTest(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tests', db_column='courseId')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pass_score = models.IntegerField(default=70)  # мінімальний відсоток для проходження
    time_limit = models.IntegerField(null=True, blank=True)  # в хвилинах
    is_active = models.BooleanField(default=True, db_column='isActive')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'CourseTests'

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class TestQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('single', 'Single Choice'),
        ('multiple', 'Multiple Choice'),
        ('text', 'Text Answer'),
    ]

    test = models.ForeignKey(CourseTest, on_delete=models.CASCADE, related_name='questions', db_column='testId')
    question = models.TextField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='single')
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'TestQuestions'
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question[:50]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='options', db_column='questionId')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False, db_column='isCorrect')
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'QuestionOptions'
        ordering = ['order']

    def __str__(self):
        return self.text


class CourseProgress(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='courseId')
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_column='studentId')
    completed_materials = models.JSONField(default=list)  # список ID матеріалів
    test_score = models.IntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False, db_column='isCompleted')
    started_at = models.DateTimeField(auto_now_add=True, db_column='startedAt')
    completed_at = models.DateTimeField(null=True, blank=True, db_column='completedAt')

    class Meta:
        db_table = 'CourseProgress'
        unique_together = ['course', 'student']

    def __str__(self):
        return f"{self.student.name} - {self.course.title}"



class CourseLesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='courseId', related_name='lessons')
    title = models.CharField(max_length=255)
    video_url = models.TextField(blank=True, null=True, db_column='videoUrl')
    video_type = models.CharField(max_length=20, default='youtube', db_column='videoType')
    duration = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'CourseLessons'
        ordering = ['order']


class CourseLessonQuestion(models.Model):
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, db_column='lessonId', related_name='questions')
    question = models.TextField()
    options = models.JSONField(default=list)
    correct_answer = models.IntegerField(default=0, db_column='correctAnswer')

    class Meta:
        db_table = 'CourseLessonQuestions'


# ─── PUZZLES ──────────────────────────────────────────────

class Puzzle(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    TYPE_CHOICES = [
        ('riddle', 'Riddle'),
        ('math', 'Math'),
        ('logic', 'Logic'),
        ('code', 'Code'),
    ]

    title = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.CharField(max_length=255)
    hint = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='riddle')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    points = models.IntegerField(default=10)
    solved_by = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    is_active = models.BooleanField(default=True, db_column='isActive')

    class Meta:
        db_table = 'Puzzles'

    def __str__(self):
        return self.title
# ─── LEARNING MATERIALS ────────────────────────────────────

class LearningMaterial(models.Model):
    TYPE_CHOICES = [('homework', 'Homework'), ('material', 'Material'), ('test', 'Test')]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='material')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subjectId')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, db_column='groupId')
    is_published = models.BooleanField(default=True, db_column='isPublished')
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'LearningMaterials'

    def __str__(self):
        return self.title


class LearningMaterialAttachment(models.Model):
    TYPE_CHOICES = [
        ('document', 'Document'), ('video', 'Video'), ('youtube', 'YouTube'),
        ('link', 'Link'), ('image', 'Image'), ('file', 'File'),
    ]

    material = models.ForeignKey(LearningMaterial, on_delete=models.CASCADE, db_column='materialId', related_name='attachments')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255)
    url = models.TextField(blank=True, null=True)
    file_size = models.CharField(max_length=50, blank=True, null=True, db_column='fileSize')

    class Meta:
        db_table = 'LearningMaterialAttachments'
