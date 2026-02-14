from rest_framework import serializers
from school.models import (
    User, Group, GroupStudent, Subject, Lesson, LessonGrade,
    Attendance, Task, TaskAttachment, TaskSubmission, SubmissionFile,
    Invoice, Notification, News, ExtraNews, StudentPoint, Team, TeamMember,
    Chat, ChatParticipant, ChatMessage, ChatMessageAttachment,
    Poll, PollOption, PollVote,
    Course, CourseLesson, CourseLessonQuestion,
    Puzzle, LearningMaterial, LearningMaterialAttachment,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'status', 'phone', 'avatar_url', 'created_at']


class StudentListSerializer(serializers.ModelSerializer):
    group = serializers.SerializerMethodField()
    avgScore = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'status', 'phone', 'created_at', 'group', 'avgScore']

    def get_group(self, obj):
        gs = obj.group_memberships.select_related('group').first()
        return gs.group.name if gs else None

    def get_avgScore(self, obj):
        grades = TaskSubmission.objects.filter(student=obj, grade__isnull=False).values_list('grade', flat=True)
        if not grades:
            return 0
        return round(sum(grades) / len(grades), 1)


class GroupSerializer(serializers.ModelSerializer):
    studentsCount = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'color', 'created_at', 'studentsCount', 'students']

    def get_studentsCount(self, obj):
        return obj.memberships.count()

    def get_students(self, obj):
        return list(
            obj.memberships.select_related('student').values(
                'student__id', 'student__name', 'student__email'
            )
        )


class SubjectSerializer(serializers.ModelSerializer):
    shortName = serializers.CharField(source='short_name')
    materialsCount = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'shortName', 'description', 'color', 'image_url', 'materialsCount']

    def get_materialsCount(self, obj):
        return Task.objects.filter(subject=obj).count()


class LessonStudentSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='student__id')
    name = serializers.CharField(source='student__name')
    attendanceStatus = serializers.CharField(allow_null=True, required=False)
    grade = serializers.IntegerField(allow_null=True, required=False)


class LessonSerializer(serializers.ModelSerializer):
    subjectName = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    subjectShort = serializers.CharField(source='subject.short_name', read_only=True, allow_null=True)
    subjectColor = serializers.CharField(source='subject.color', read_only=True, allow_null=True)
    groupName = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    groupColor = serializers.CharField(source='group.color', read_only=True, allow_null=True)
    scheduledDate = serializers.DateField(source='scheduled_date')
    startTime = serializers.CharField(source='start_time')
    endTime = serializers.CharField(source='end_time')
    meetingLink = serializers.CharField(source='meeting_link', allow_null=True, required=False)
    students = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'scheduledDate', 'startTime', 'endTime',
            'meetingLink', 'status', 'subjectName', 'subjectShort', 'subjectColor',
            'groupName', 'groupColor', 'students',
        ]

    def get_students(self, obj):
        if not obj.group_id:
            return []
        students = GroupStudent.objects.filter(group_id=obj.group_id).select_related('student')
        result = []
        for gs in students:
            att = Attendance.objects.filter(lesson=obj, student=gs.student).first()
            lg = LessonGrade.objects.filter(lesson=obj, student=gs.student).first()
            result.append({
                'id': gs.student.id,
                'name': gs.student.name,
                'attendanceStatus': att.status if att else None,
                'grade': lg.grade if lg else None,
            })
        return result


class TaskSerializer(serializers.ModelSerializer):
    subjectName = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    subjectShort = serializers.CharField(source='subject.short_name', read_only=True, allow_null=True)
    subjectColor = serializers.CharField(source='subject.color', read_only=True, allow_null=True)
    groupName = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    groupColor = serializers.CharField(source='group.color', read_only=True, allow_null=True)
    groupId = serializers.IntegerField(source='group_id', allow_null=True)
    dueDate = serializers.DateTimeField(source='due_date', allow_null=True)
    maxGrade = serializers.IntegerField(source='max_grade')
    totalStudents = serializers.SerializerMethodField()
    submittedCount = serializers.SerializerMethodField()
    gradedCount = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'type', 'dueDate', 'maxGrade',
            'subjectName', 'subjectShort', 'subjectColor',
            'groupName', 'groupId', 'groupColor',
            'totalStudents', 'submittedCount', 'gradedCount',
        ]

    def get_totalStudents(self, obj):
        if not obj.group_id:
            return 0
        return GroupStudent.objects.filter(group_id=obj.group_id).count()

    def get_submittedCount(self, obj):
        return obj.submissions.count()

    def get_gradedCount(self, obj):
        return obj.submissions.filter(status='graded').count()


class StudentTaskSerializer(TaskSerializer):
    """Extended task serializer that includes submission status for a specific student."""
    submissionStatus = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    submittedAt = serializers.SerializerMethodField()
    teacherComment = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['submissionStatus', 'grade', 'submittedAt', 'teacherComment']

    def get_submissionStatus(self, obj):
        sub = getattr(obj, '_student_submission', None)
        return sub.status if sub else None

    def get_grade(self, obj):
        sub = getattr(obj, '_student_submission', None)
        return sub.grade if sub else None

    def get_submittedAt(self, obj):
        sub = getattr(obj, '_student_submission', None)
        return sub.submitted_at.isoformat() if sub and sub.submitted_at else None

    def get_teacherComment(self, obj):
        sub = getattr(obj, '_student_submission', None)
        return sub.teacher_comment if sub else None


class SubmissionFileSerializer(serializers.ModelSerializer):
    fileName = serializers.CharField(source='file_name')
    fileUrl = serializers.CharField(source='file_url')
    fileSize = serializers.CharField(source='file_size', allow_null=True)
    fileType = serializers.CharField(source='file_type')

    class Meta:
        model = SubmissionFile
        fields = ['id', 'fileName', 'fileUrl', 'fileSize', 'fileType']


class TaskSubmissionSerializer(serializers.ModelSerializer):
    studentName = serializers.CharField(source='student.name', read_only=True)
    studentEmail = serializers.CharField(source='student.email', read_only=True)
    taskTitle = serializers.CharField(source='task.title', read_only=True)
    maxGrade = serializers.IntegerField(source='task.max_grade', read_only=True)
    studentGroup = serializers.SerializerMethodField()
    teacherComment = serializers.CharField(source='teacher_comment', allow_null=True)
    submittedAt = serializers.DateTimeField(source='submitted_at', allow_null=True)
    gradedAt = serializers.DateTimeField(source='graded_at', allow_null=True)
    files = SubmissionFileSerializer(many=True, read_only=True)

    class Meta:
        model = TaskSubmission
        fields = [
            'id', 'task_id', 'student_id', 'comment', 'status', 'grade',
            'teacherComment', 'submittedAt', 'gradedAt',
            'studentName', 'studentEmail', 'taskTitle', 'maxGrade', 'studentGroup',
            'files',
        ]

    def get_studentGroup(self, obj):
        gs = obj.student.group_memberships.select_related('group').first()
        return gs.group.name if gs else None


class InvoiceSerializer(serializers.ModelSerializer):
    studentName = serializers.CharField(source='student.name', read_only=True)
    studentEmail = serializers.CharField(source='student.email', read_only=True)
    studentGroup = serializers.SerializerMethodField()
    groupColor = serializers.SerializerMethodField()
    paidAmount = serializers.DecimalField(source='paid_amount', max_digits=10, decimal_places=2)
    currentInstallment = serializers.IntegerField(source='current_installment')
    dueDate = serializers.DateField(source='due_date', allow_null=True)
    paidAt = serializers.DateTimeField(source='paid_at', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'student_id', 'amount', 'paidAmount', 'installments',
            'currentInstallment', 'description', 'status', 'dueDate', 'paidAt', 'createdAt',
            'studentName', 'studentEmail', 'studentGroup', 'groupColor',
        ]

    def get_studentGroup(self, obj):
        gs = obj.student.group_memberships.select_related('group').first()
        return gs.group.name if gs else None

    def get_groupColor(self, obj):
        gs = obj.student.group_memberships.select_related('group').first()
        return gs.group.color if gs else None


class ExtraNewsSerializer(serializers.ModelSerializer):
    mediaType = serializers.CharField(source='media_type', allow_null=True)
    mediaUrl = serializers.CharField(source='media_url', allow_null=True)

    class Meta:
        model = ExtraNews
        fields = ['id', 'title', 'description', 'mediaType', 'mediaUrl']


class LeaderboardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    points = serializers.IntegerField()
    rank = serializers.IntegerField()


# ─── NEWS ────────────────────────────────────────────────

class NewsSerializer(serializers.ModelSerializer):
    isPublished = serializers.BooleanField(source='is_published')
    imageUrl = serializers.CharField(source='image_url', allow_null=True, required=False)
    publishedAt = serializers.DateTimeField(source='published_at', allow_null=True, required=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = News
        fields = ['id', 'title', 'content', 'imageUrl', 'category', 'isPublished', 'publishedAt', 'createdAt']


# ─── CHAT ────────────────────────────────────────────────

class ChatMessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessageAttachment
        fields = ['id', 'type', 'name', 'url', 'size']


class ChatMessageSerializer(serializers.ModelSerializer):
    senderId = serializers.IntegerField(source='sender_id')
    senderName = serializers.CharField(source='sender.name', read_only=True)
    isAdmin = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()
    attachments = ChatMessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'senderId', 'senderName', 'content', 'timestamp', 'isAdmin', 'attachments']

    def get_isAdmin(self, obj):
        return obj.sender.role == 'admin' if obj.sender else False

    def get_timestamp(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%H:%M')
        return ''


class ChatParticipantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id')
    name = serializers.CharField(source='user.name')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = ChatParticipant
        fields = ['id', 'name', 'email']


class ChatListSerializer(serializers.ModelSerializer):
    participants = ChatParticipantSerializer(many=True, read_only=True)
    lastMessage = serializers.SerializerMethodField()
    unreadCount = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'type', 'name', 'participants', 'lastMessage', 'unreadCount']

    def get_lastMessage(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return ChatMessageSerializer(msg).data
        return None

    def get_unreadCount(self, obj):
        return 0  # Simplified -- could track per-user read status


# ─── POLLS ───────────────────────────────────────────────

class PollOptionSerializer(serializers.ModelSerializer):
    votes = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ['id', 'text', 'votes']

    def get_votes(self, obj):
        return obj.votes.count()


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    targetType = serializers.CharField(source='target_type')
    targetGroupId = serializers.SerializerMethodField()
    targetGroupName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source='is_anonymous')
    isMultipleChoice = serializers.BooleanField(source='is_multiple_choice')
    endsAt = serializers.DateField(source='ends_at')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    totalVotes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            'id', 'title', 'description', 'options', 'targetType',
            'targetGroupId', 'targetGroupName', 'isAnonymous', 'isMultipleChoice',
            'status', 'endsAt', 'createdAt', 'totalVotes',
        ]

    def get_targetGroupId(self, obj):
        return str(obj.target_group_id) if obj.target_group_id else ''

    def get_targetGroupName(self, obj):
        if obj.target_type == 'all':
            return 'All students'
        return obj.target_group.name if obj.target_group else ''

    def get_totalVotes(self, obj):
        return PollVote.objects.filter(option__poll=obj).count()


# ─── COURSES ─────────────────────────────────────────────

class CourseLessonQuestionSerializer(serializers.ModelSerializer):
    correctAnswer = serializers.IntegerField(source='correct_answer')

    class Meta:
        model = CourseLessonQuestion
        fields = ['id', 'question', 'options', 'correctAnswer']


class CourseLessonSerializer(serializers.ModelSerializer):
    videoUrl = serializers.CharField(source='video_url', allow_null=True)
    videoType = serializers.CharField(source='video_type')
    test = CourseLessonQuestionSerializer(source='questions', many=True, read_only=True)

    class Meta:
        model = CourseLesson
        fields = ['id', 'title', 'videoUrl', 'videoType', 'duration', 'description', 'order', 'test']


class CourseSerializer(serializers.ModelSerializer):
    subjectId = serializers.SerializerMethodField()
    subjectName = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    subjectColor = serializers.CharField(source='subject.color', read_only=True, allow_null=True)
    isPublished = serializers.BooleanField(source='is_published')
    studentsEnrolled = serializers.IntegerField(source='students_enrolled')
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'subjectId', 'subjectName', 'subjectColor',
            'thumbnail', 'isPublished', 'studentsEnrolled', 'lessons',
        ]

    def get_subjectId(self, obj):
        return str(obj.subject_id) if obj.subject_id else ''


# ─── TEAMS ───────────────────────────────────────────────

class TeamMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='student.id')
    name = serializers.CharField(source='student.name')
    email = serializers.CharField(source='student.email')
    points = serializers.SerializerMethodField()

    class Meta:
        model = TeamMember
        fields = ['id', 'name', 'email', 'points']

    def get_points(self, obj):
        from django.db.models.functions import Coalesce
        from django.db.models import Sum
        return StudentPoint.objects.filter(student=obj.student).aggregate(
            s=Coalesce(Sum('points'), 0)
        )['s']


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)
    totalPoints = serializers.IntegerField(source='total_points')
    groupId = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    color = serializers.CharField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'color', 'groupId', 'group', 'members', 'totalPoints', 'rank']

    def get_groupId(self, obj):
        return str(obj.group_id) if obj.group_id else ''

    def get_group(self, obj):
        return obj.group.name if obj.group else ''

    def get_rank(self, obj):
        # Calculate rank based on total_points
        higher = Team.objects.filter(total_points__gt=obj.total_points).count()
        return higher + 1


# ─── PUZZLES ─────────────────────────────────────────────

class PuzzleSerializer(serializers.ModelSerializer):
    isActive = serializers.BooleanField(source='is_active')
    solvedBy = serializers.IntegerField(source='solved_by')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Puzzle
        fields = ['id', 'type', 'title', 'question', 'answer', 'hint', 'difficulty', 'points', 'isActive', 'solvedBy', 'createdAt']


# ─── LEARNING MATERIALS ──────────────────────────────────

class LearningMaterialAttachmentSerializer(serializers.ModelSerializer):
    fileSize = serializers.CharField(source='file_size', allow_null=True)

    class Meta:
        model = LearningMaterialAttachment
        fields = ['id', 'type', 'name', 'url', 'fileSize']


class LearningMaterialSerializer(serializers.ModelSerializer):
    subjectId = serializers.SerializerMethodField()
    subjectName = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    subjectColor = serializers.CharField(source='subject.color', read_only=True, allow_null=True)
    groupId = serializers.SerializerMethodField()
    groupName = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    isPublished = serializers.BooleanField(source='is_published')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    attachments = LearningMaterialAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = LearningMaterial
        fields = [
            'id', 'title', 'description', 'type', 'subjectId', 'subjectName', 'subjectColor',
            'groupId', 'groupName', 'isPublished', 'createdAt', 'attachments',
        ]

    def get_subjectId(self, obj):
        return str(obj.subject_id) if obj.subject_id else ''

    def get_groupId(self, obj):
        return str(obj.group_id) if obj.group_id else ''


# ─── ADMINISTRATORS ──────────────────────────────────────

class AdminUserSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    avatarUrl = serializers.CharField(source='avatar_url', allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'status', 'phone', 'avatarUrl', 'createdAt']
