import bcrypt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from school.models import (
    User, Group, GroupStudent, Subject, Lesson, Task, LessonGrade,
    Attendance, Invoice, Notification, News, ExtraNews, StudentPoint,
    Team, TeamMember, Chat, ChatMessage, ChatParticipant, Poll,
    PollOption, PollVote, Course, CourseLesson, Puzzle, LearningMaterial
)
# ===== AUTHENTICATION =====

@api_view(['POST'])
@permission_classes([AllowAny])
def auth_login(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')
    if not email or not password:
        return Response({'success': False, 'error': "Email та пароль обов'язкові"}, status=400)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Невірний email або пароль'}, status=401)
    try:
        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            return Response({'success': False, 'error': 'Невірний email або пароль'}, status=401)
    except Exception:
        return Response({'success': False, 'error': 'Невірний email або пароль'}, status=401)
    return Response({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_register(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')
    name = request.data.get('name', '')
    if not email or not password:
        return Response({'success': False, 'error': "Email та пароль обов'язкові"}, status=400)
    if len(password) < 6:
        return Response({'success': False, 'error': 'Пароль має бути не менше 6 символів'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'success': False, 'error': 'Користувач з таким email вже існує'}, status=400)
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User.objects.create(email=email, password=hashed_password, name=name or email.split('@')[0], role='student', status='active')
    return Response({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_logout(request):
    return Response({'success': True}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_me(request):
    return Response({'success': True, 'user': None}, status=200)


# ===== ADMINISTRATORS =====

@api_view(['GET', 'POST'])
def administrators_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        if not name or not email or not password:
            return Response({'success': False, 'error': 'Всі поля обов\'язкові'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'success': False, 'error': 'Користувач з таким email вже існує'}, status=400)
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(email=email, password=hashed_password, name=name, role='admin', status='active')
        return Response({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}}, status=201)
    admins = User.objects.filter(role='admin')
    return Response([{'id': admin.id, 'email': admin.email, 'name': admin.name, 'role': admin.role} for admin in admins])


@api_view(['GET', 'PUT', 'DELETE'])
def administrator_detail(request, pk):
    try:
        admin = User.objects.get(id=pk, role='admin')
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Адміністратор не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': admin.id, 'email': admin.email, 'name': admin.name, 'role': admin.role})
    if request.method == 'PUT':
        admin.name = request.data.get('name', admin.name)
        admin.email = request.data.get('email', admin.email)
        admin.save()
        return Response({'success': True, 'user': {'id': admin.id, 'email': admin.email, 'name': admin.name}})
    if request.method == 'DELETE':
        admin.delete()
        return Response({'success': True})


# ===== STUDENTS =====

@api_view(['GET'])
@permission_classes([AllowAny])
def students_list(request):
    students = User.objects.filter(role='student')
    return Response([{'id': student.id, 'email': student.email, 'name': student.name, 'role': student.role, 'status': student.status} for student in students])


@api_view(['GET'])
def student_detail(request, pk):
    try:
        student = User.objects.get(id=pk, role='student')
        return Response({'id': student.id, 'email': student.email, 'name': student.name, 'role': student.role, 'status': student.status})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)


# ===== GROUPS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def groups_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        description = request.data.get('description', '')
        color = request.data.get('color', '#7c3aed')
        schedule = request.data.get('schedule', '')
        if not name:
            return Response({'success': False, 'error': 'Назва групи обов\'язкова'}, status=400)
        group = Group.objects.create(name=name, description=description, color=color, schedule=schedule)
        return Response({'success': True, 'group': {'id': group.id, 'name': group.name, 'description': group.description, 'color': group.color, 'schedule': group.schedule, 'created_at': group.created_at}}, status=201)
    groups = Group.objects.all()
    return Response([{'id': group.id, 'name': group.name, 'description': group.description, 'color': group.color, 'schedule': group.schedule, 'created_at': group.created_at} for group in groups])


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def group_detail(request, pk):
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': group.id, 'name': group.name, 'description': group.description, 'color': group.color, 'schedule': group.schedule, 'created_at': group.created_at})
    if request.method == 'PUT':
        group.name = request.data.get('name', group.name)
        group.description = request.data.get('description', group.description)
        group.color = request.data.get('color', group.color)
        group.schedule = request.data.get('schedule', group.schedule)
        group.save()
        return Response({'success': True, 'group': {'id': group.id, 'name': group.name}})
    if request.method == 'DELETE':
        group.delete()
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([AllowAny])
def group_students(request, pk):
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)
    try:
        students = GroupStudent.objects.filter(group=group).select_related('student')
        return Response([{'id': gs.student.id, 'email': gs.student.email, 'name': gs.student.name, 'role': gs.student.role} for gs in students])
    except:
        return Response([])


# ===== SUBJECTS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def subjects_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        short_name = request.data.get('short_name', '')
        if not name or not short_name:
            return Response({'success': False, 'error': 'Назва та скорочення обов\'язкові'}, status=400)
        subject = Subject.objects.create(name=name, short_name=short_name, description=request.data.get('description', ''), color=request.data.get('color', '#7c3aed'))
        return Response({'success': True, 'subject': {'id': subject.id, 'name': subject.name, 'short_name': subject.short_name}}, status=201)
    subjects = Subject.objects.all()
    return Response([{'id': s.id, 'name': s.name, 'short_name': s.short_name, 'description': s.description, 'color': s.color} for s in subjects])


@api_view(['GET', 'PUT', 'DELETE'])
def subject_detail(request, pk):
    try:
        subject = Subject.objects.get(id=pk)
    except Subject.DoesNotExist:
        return Response({'success': False, 'error': 'Предмет не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': subject.id, 'name': subject.name, 'short_name': subject.short_name, 'description': subject.description, 'color': subject.color})
    if request.method == 'PUT':
        subject.name = request.data.get('name', subject.name)
        subject.short_name = request.data.get('short_name', subject.short_name)
        subject.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        subject.delete()
        return Response({'success': True})


# ===== LESSONS =====

@api_view(['GET', 'POST'])
def lessons_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва урока обов\'язкова'}, status=400)
        lesson = Lesson.objects.create(title=title, description=request.data.get('description', ''), scheduled_date=request.data.get('scheduled_date'), start_time=request.data.get('start_time'), end_time=request.data.get('end_time'))
        return Response({'success': True, 'lesson': {'id': lesson.id, 'title': lesson.title}}, status=201)
    lessons = Lesson.objects.all()
    return Response([{'id': l.id, 'title': l.title, 'description': l.description, 'status': l.status} for l in lessons])


@api_view(['GET', 'PUT', 'DELETE'])
def lesson_detail(request, pk):
    try:
        lesson = Lesson.objects.get(id=pk)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': lesson.id, 'title': lesson.title, 'description': lesson.description, 'status': lesson.status})
    if request.method == 'PUT':
        lesson.title = request.data.get('title', lesson.title)
        lesson.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        lesson.delete()
        return Response({'success': True})


@api_view(['GET'])
def lesson_grades(request, pk):
    try:
        lesson = Lesson.objects.get(id=pk)
        grades = LessonGrade.objects.filter(lesson=lesson)
        return Response([{'id': g.id, 'student': g.student.name, 'grade': g.grade, 'comment': g.comment} for g in grades])
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдений'}, status=404)


# ===== TASKS =====

@api_view(['GET', 'POST'])
def tasks_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва завдання обов\'язкова'}, status=400)
        task = Task.objects.create(title=title, description=request.data.get('description', ''), type=request.data.get('type', 'homework'))
        return Response({'success': True, 'task': {'id': task.id, 'title': task.title}}, status=201)
    tasks = Task.objects.all()
    return Response([{'id': t.id, 'title': t.title, 'type': t.type, 'description': t.description} for t in tasks])


@api_view(['GET'])
def task_submissions(request, pk):
    try:
        task = Task.objects.get(id=pk)
        submissions = task.submissions.all()
        return Response([{'id': s.id, 'student': s.student.name, 'status': s.status, 'grade': s.grade} for s in submissions])
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)


@api_view(['POST'])
def grade_submission(request, pk):
    return Response({'success': True})


# ===== GRADES & ATTENDANCE =====

@api_view(['GET'])
def grades_list(request):
    grades = LessonGrade.objects.all()
    return Response([{'id': g.id, 'student': g.student.name, 'lesson': g.lesson.title, 'grade': g.grade} for g in grades])


@api_view(['GET'])
def attendance_list(request):
    attendance = Attendance.objects.all()
    return Response([{'id': a.id, 'student': a.student.name, 'lesson': a.lesson.title, 'status': a.status} for a in attendance])


# ===== INVOICES =====

@api_view(['GET'])
def invoices_list(request):
    invoices = Invoice.objects.all()
    return Response([{'id': i.id, 'student': i.student.name, 'amount': str(i.amount), 'status': i.status} for i in invoices])


@api_view(['GET'])
def invoices_history(request):
    invoices = Invoice.objects.all()
    return Response([{'id': i.id, 'student': i.student.name, 'amount': str(i.amount), 'paid_amount': str(i.paid_amount), 'status': i.status} for i in invoices])


# ===== ADMIN & STATS =====

@api_view(['GET'])
def admin_stats(request):
    return Response({'students': User.objects.filter(role='student').count(), 'admins': User.objects.filter(role='admin').count(), 'groups': Group.objects.count()})


@api_view(['GET'])
def leaderboard(request):
    points = StudentPoint.objects.values('student__name').annotate(total=sum('points')).order_by('-total')[:10]
    return Response(list(points))


# ===== NEWS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def news_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        if not title or not content:
            return Response({'success': False, 'error': 'Заголовок та вміст обов\'язкові'}, status=400)
        news = News.objects.create(title=title, content=content, is_published=True)
        return Response({'success': True, 'news': {'id': news.id, 'title': news.title}}, status=201)
    news_list_obj = News.objects.filter(is_published=True)
    return Response([{'id': n.id, 'title': n.title, 'content': n.content[:100], 'created_at': n.created_at} for n in news_list_obj])


@api_view(['GET', 'PUT', 'DELETE'])
def news_detail(request, pk):
    try:
        news = News.objects.get(id=pk)
    except News.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': news.id, 'title': news.title, 'content': news.content, 'created_at': news.created_at})
    if request.method == 'PUT':
        news.title = request.data.get('title', news.title)
        news.content = request.data.get('content', news.content)
        news.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        news.delete()
        return Response({'success': True})


# ===== EXTRA NEWS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def extra_news_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Заголовок обов\'язковий'}, status=400)
        extra_news = ExtraNews.objects.create(title=title, description=request.data.get('description', ''), media_type=request.data.get('media_type'), media_url=request.data.get('media_url'))
        return Response({'success': True, 'news': {'id': extra_news.id, 'title': extra_news.title}}, status=201)
    extra_news_list_obj = ExtraNews.objects.filter(is_active=True)
    return Response([{'id': n.id, 'title': n.title, 'media_type': n.media_type, 'media_url': n.media_url} for n in extra_news_list_obj])


@api_view(['GET', 'PUT', 'DELETE'])
def extra_news_detail(request, pk):
    try:
        extra_news = ExtraNews.objects.get(id=pk)
    except ExtraNews.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': extra_news.id, 'title': extra_news.title, 'description': extra_news.description, 'media_type': extra_news.media_type})
    if request.method == 'PUT':
        extra_news.title = request.data.get('title', extra_news.title)
        extra_news.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        extra_news.delete()
        return Response({'success': True})


# ===== CHATS =====

@api_view(['GET', 'POST'])
def chats_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        chat = Chat.objects.create(type='group', name=name)
        return Response({'success': True, 'chat': {'id': chat.id, 'name': chat.name}}, status=201)
    chats = Chat.objects.all()
    return Response([{'id': c.id, 'name': c.name, 'type': c.type} for c in chats])


@api_view(['GET', 'PUT', 'DELETE'])
def chat_detail(request, pk):
    try:
        chat = Chat.objects.get(id=pk)
    except Chat.DoesNotExist:
        return Response({'success': False, 'error': 'Чат не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': chat.id, 'name': chat.name, 'type': chat.type})
    if request.method == 'PUT':
        chat.name = request.data.get('name', chat.name)
        chat.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        chat.delete()
        return Response({'success': True})


@api_view(['GET', 'POST'])
def chat_messages(request, pk):
    try:
        chat = Chat.objects.get(id=pk)
    except Chat.DoesNotExist:
        return Response({'success': False, 'error': 'Чат не знайдений'}, status=404)
    if request.method == 'POST':
        content = request.data.get('content', '')
        sender_id = request.data.get('sender_id')
        if not sender_id:
            return Response({'success': False, 'error': 'Sender ID обов\'язковий'}, status=400)
        try:
            sender = User.objects.get(id=sender_id)
            message = ChatMessage.objects.create(chat=chat, sender=sender, content=content)
            return Response({'success': True, 'message': {'id': message.id, 'content': message.content}}, status=201)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Користувач не знайдений'}, status=404)
    messages = chat.messages.all()
    return Response([{'id': m.id, 'sender': m.sender.name, 'content': m.content, 'created_at': m.created_at} for m in messages])


# ===== POLLS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def polls_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Заголовок обов\'язковий'}, status=400)
        poll = Poll.objects.create(title=title, description=request.data.get('description', ''), ends_at=request.data.get('ends_at'))
        return Response({'success': True, 'poll': {'id': poll.id, 'title': poll.title}}, status=201)
    polls = Poll.objects.all()
    return Response([{'id': p.id, 'title': p.title, 'status': p.status} for p in polls])


@api_view(['GET'])
def poll_detail(request, pk):
    try:
        poll = Poll.objects.get(id=pk)
        options = poll.options.all()
        return Response({'id': poll.id, 'title': poll.title, 'options': [{'id': o.id, 'text': o.text} for o in options]})
    except Poll.DoesNotExist:
        return Response({'success': False, 'error': 'Опитування не знайдене'}, status=404)


@api_view(['POST'])
def poll_vote(request, pk):
    try:
        option = PollOption.objects.get(id=pk)
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'success': False, 'error': 'Student ID обов\'язковий'}, status=400)
        student = User.objects.get(id=student_id)
        vote = PollVote.objects.create(option=option, student=student)
        return Response({'success': True, 'vote': {'id': vote.id}}, status=201)
    except (PollOption.DoesNotExist, User.DoesNotExist):
        return Response({'success': False, 'error': 'Not found'}, status=404)


# ===== COURSES =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def courses_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва курсу обов\'язкова'}, status=400)
        course = Course.objects.create(title=title, description=request.data.get('description', ''))
        return Response({'success': True, 'course': {'id': course.id, 'title': course.title}}, status=201)
    courses = Course.objects.all()
    return Response([{'id': c.id, 'title': c.title, 'description': c.description, 'is_published': c.is_published} for c in courses])


@api_view(['GET', 'PUT', 'DELETE'])
def course_detail(request, pk):
    try:
        course = Course.objects.get(id=pk)
    except Course.DoesNotExist:
        return Response({'success': False, 'error': 'Курс не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': course.id, 'title': course.title, 'description': course.description, 'is_published': course.is_published})
    if request.method == 'PUT':
        course.title = request.data.get('title', course.title)
        course.description = request.data.get('description', course.description)
        course.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        course.delete()
        return Response({'success': True})


# ===== TEAMS =====

@api_view(['GET', 'POST'])
def teams_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        if not name:
            return Response({'success': False, 'error': 'Назва команди обов\'язкова'}, status=400)
        team = Team.objects.create(name=name, description=request.data.get('description', ''), color=request.data.get('color', '#FF9A00'))
        return Response({'success': True, 'team': {'id': team.id, 'name': team.name}}, status=201)
    teams = Team.objects.all()
    return Response([{'id': t.id, 'name': t.name, 'total_points': t.total_points} for t in teams])


@api_view(['GET', 'PUT', 'DELETE'])
def team_detail(request, pk):
    try:
        team = Team.objects.get(id=pk)
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': team.id, 'name': team.name, 'description': team.description, 'total_points': team.total_points})
    if request.method == 'PUT':
        team.name = request.data.get('name', team.name)
        team.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        team.delete()
        return Response({'success': True})


@api_view(['GET'])
def team_members(request, pk):
    try:
        team = Team.objects.get(id=pk)
        members = TeamMember.objects.filter(team=team)
        return Response([{'id': m.student.id, 'name': m.student.name, 'email': m.student.email} for m in members])
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)


# ===== PUZZLES =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def puzzles_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        question = request.data.get('question', '')
        answer = request.data.get('answer', '')
        if not all([title, question, answer]):
            return Response({'success': False, 'error': 'Всі поля обов\'язкові'}, status=400)
        puzzle = Puzzle.objects.create(title=title, question=question, answer=answer, type=request.data.get('type', 'riddle'), difficulty=request.data.get('difficulty', 'medium'))
        return Response({'success': True, 'puzzle': {'id': puzzle.id, 'title': puzzle.title}}, status=201)
    puzzles = Puzzle.objects.all()
    return Response([{'id': p.id, 'title': p.title, 'difficulty': p.difficulty, 'points': p.points} for p in puzzles])


@api_view(['GET'])
def puzzle_detail(request, pk):
    try:
        puzzle = Puzzle.objects.get(id=pk)
        return Response({'id': puzzle.id, 'title': puzzle.title, 'question': puzzle.question, 'hint': puzzle.hint, 'difficulty': puzzle.difficulty, 'points': puzzle.points})
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)


@api_view(['POST'])
def puzzle_answer(request, pk):
    try:
        puzzle = Puzzle.objects.get(id=pk)
        answer = request.data.get('answer', '').strip().lower()
        correct_answer = puzzle.answer.strip().lower()
        if answer == correct_answer:
            puzzle.solved_by += 1
            puzzle.save()
            return Response({'success': True, 'correct': True, 'points': puzzle.points})
        return Response({'success': False, 'correct': False}, status=400)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)


# ===== LEARNING MATERIALS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def learning_materials_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва обов\'язкова'}, status=400)
        material = LearningMaterial.objects.create(title=title, description=request.data.get('description', ''), type=request.data.get('type', 'material'))
        return Response({'success': True, 'material': {'id': material.id, 'title': material.title}}, status=201)
    materials = LearningMaterial.objects.filter(is_published=True)
    return Response([{'id': m.id, 'title': m.title, 'type': m.type, 'description': m.description} for m in materials])


@api_view(['GET', 'PUT', 'DELETE'])
def learning_material_detail(request, pk):
    try:
        material = LearningMaterial.objects.get(id=pk)
    except LearningMaterial.DoesNotExist:
        return Response({'success': False, 'error': 'Матеріал не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': material.id, 'title': material.title, 'description': material.description, 'type': material.type})
    if request.method == 'PUT':
        material.title = request.data.get('title', material.title)
        material.description = request.data.get('description', material.description)
        material.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        material.delete()
        return Response({'success': True})


# ===== NOTIFICATIONS =====

@api_view(['GET'])
def notifications_list(request):
    notifications = Notification.objects.all()
    return Response([{'id': n.id, 'title': n.title, 'message': n.message, 'is_read': n.is_read, 'created_at': n.created_at} for n in notifications])


@api_view(['POST'])
def notification_read(request, pk):
    try:
        notification = Notification.objects.get(id=pk)
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'success': False, 'error': 'Сповіщення не знайдено'}, status=404)