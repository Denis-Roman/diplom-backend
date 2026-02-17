import bcrypt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import models
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from school.models import (
    User, Group, GroupStudent, Subject, Lesson, Task, LessonGrade,
    Attendance, Invoice, Notification, News, ExtraNews, StudentPoint,
    Team, TeamMember, Chat, ChatMessage, Poll,
    PollOption, CourseMaterial, CourseTest, TestQuestion, QuestionOption, PollVote, Course, Puzzle, LearningMaterial
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import News
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.hashers import make_password, check_password

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from school.models import User

permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def administrator_detail(request, pk):
    try:
        admin = User.objects.get(id=pk, role__in=['admin', 'superadmin'])
    except User.DoesNotExist:
        return Response({'error': 'Адміністратор не знайдений'}, status=404)

    # GET - Деталі адміна
    if request.method == 'GET':
        return Response({
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "is_active": admin.is_active,
            "is_superadmin": admin.is_superadmin,
            "created_at": admin.created_at,
        })

    # PUT - Оновлення адміна (OK міняти name/email/pass, не роль/суперадмін)
    if request.method == 'PUT':
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        if name: admin.name = name
        if email:
            if User.objects.exclude(id=admin.id).filter(email=email).exists():
                return Response({'error': 'Email вже існує.'}, status=400)
            admin.email = email
        if password and len(password) >= 6:
            admin.password = make_password(password)
        admin.save()
        return Response({'success': True})

    # DELETE - Видалення адміна (тільки не супер-адміна)
    if request.method == 'DELETE':
        if admin.is_superadmin:
            return Response({'error': "Неможливо видалити супер-адміна."}, status=403)
        admin.delete()
        return Response({'success': True})

@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def news_update(request, pk):
    """
    Оновлення (редагування) новини, підтримує multipart/form-data (upload фото з комп'ютера)
    """
    news = get_object_or_404(News, pk=pk)

    # Текстові/логічні поля
    news.title = request.data.get('title', news.title)
    news.content = request.data.get('content', news.content)
    news.category = request.data.get('category', news.category)
    news.is_published = request.data.get('is_published', news.is_published)
    news.image_url = request.data.get('image_url', news.image_url)
    news.video_url = request.data.get('video_url', news.video_url)
    news.link = request.data.get('link', news.link)
    # Обробити булеве (is_published може бути рядком)
    if isinstance(news.is_published, str):
        news.is_published = news.is_published in ["true", "True", "1"]

    # Якщо є новий файл ‒ записати
    if request.FILES.get('image_file'):
        news.image_file = request.FILES['image_file']

    news.save()
    return Response({'success': True, 'news_id': news.id})

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def news_create(request):
    title = request.data.get('title', '').strip()
    image_file = request.FILES.get('image_file')
    content = request.data.get('content', '').strip()
    category = request.data.get('category', '').strip()
    is_published = request.data.get('is_published', True)

    # Зображення з файла
    image_file = request.FILES.get('image_file')
    is_published_str = request.POST.get('is_published', 'false')
    is_published = True if is_published_str.lower() == 'true' else False
    news = News.objects.create(
        title=title,
        content=content,
        category=category,
        image_file=image_file,  # якщо є
        image_url=image_url,
        video_url=video_url,
        link=link,
        is_published=is_published,  # <- ПРОПИСУЄШ boolean, НЕ string!
    )
    return Response({'success': True, 'news_id': news.id}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # для продакшн, для тест��в можеш вмикати AllowAny
def create_invoice(request):
    students = request.data.get('student_ids', [])
    amount = request.data.get('amount')
    description = request.data.get('description', '')
    installments = int(request.data.get('installments', 1))
    due_date = request.data.get('due_date')
    if not students or not amount or not due_date:
        return Response({'success': False, 'error': 'Всі поля обов’язкові'}, status=400)

    # Перевірка дати платежу проти дати реєстрації
    for sid in students:
        student = User.objects.get(id=sid)
        reg_date = student.registered_at
        d = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
        if d < reg_date:
            return Response({
                'success': False,
                'error': f'Дата платежу для {student.name} раніше дати реєстрації: {reg_date}'
            }, status=400)

    # Створення рахунка для кожного студента
    result = []
    for sid in students:
        student = User.objects.get(id=sid)
        first_due = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
        for i in range(installments):
            current_due = first_due + datetime.timedelta(days=30 * i)
            inv = Invoice.objects.create(
                student=student,
                amount=amount,
                paid_amount=0,
                installments=installments,
                current_installment=i+1,
                description=description,
                status='pending',
                due_date=current_due,
            )
            # Створити Notification (TODO: e-mail/ інша розсилка)
            Notification.objects.create(
                user=student,
                type='invoice',
                title='Новий рахунок',
                message=f'��ам виставлено рахунок на {amount} грн.',
            )
            result.append({'invoice_id': inv.id, 'installment': i+1})
    return Response({'success': True, 'created': result}, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices_list(request):
    invoices = Invoice.objects.select_related('student').order_by('-created_at').all()
    data = []
    for i in invoices:
        data.append({
            'id': i.id,
            'studentId': i.student.id,
            'studentName': i.student.name,
            'studentEmail': i.student.email,
            'amount': float(i.amount),
            'paidAmount': float(i.paid_amount),
            'installments': i.installments,
            'currentInstallment': i.current_installment,
            'status': i.status,
            'dueDate': i.due_date.isoformat() if i.due_date else '',
            'createdAt': i.created_at.isoformat() if i.created_at else '',
            'description': i.description or '',
        })
    return Response(data)

# + додай у urls.py:
# path('api/invoices/', views.invoices_list),
# path('api/invoices/create/', views.create_invoice),

# ===== AUTHENTICATION =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def administrators_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').lower()
        password = request.data.get('password', '')

        if not (name and email and password):
            return Response({'error': 'Всі поля обовʼязкові!'}, status=400)
        if len(password) < 6:
            return Response({'error': 'Пароль має бути не менше 6 символів!'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email вже існує.'}, status=400)
        user = User.objects.create(
            name=name,
            email=email,
            password=make_password(password),  # Хешування!
            is_active=True,
            is_superadmin=False,
            role='admin',
            created_at=timezone.now()
        )
        return Response({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
            "created_at": user.created_at,
        }, status=201)

    # GET: спи��ок адміністраторів і суперадмінів
    admins = User.objects.filter(role__in=['admin', 'superadmin'])
    return Response([
        {
            "id": u.id, "name": u.name, "email": u.email,
            "is_active": u.is_active,
            "is_superadmin": u.is_superadmin,
            "created_at": u.created_at
        } for u in admins
    ])


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
    user = User.objects.create(
        email=email,
        password=hashed_password,
        name=name or email.split('@')[0],
        role='student',
        status='active',
        is_active = True,
    )
    return Response(
        {'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}},
        status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_logout(request):
    return Response({'success': True}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_me(request):
    return Response({'success': True, 'user': None}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_toggle_status(request, pk):
    try:
        user = User.objects.get(pk=pk)
        if user.is_superadmin:
            return Response({"error": "Неможливо заблокувати супер-адміна."}, status=400)
        user.is_active = not user.is_active
        user.save()
        return Response({"success": True})
    except User.DoesNotExist:
        return Response({"error": "Admin not found."}, status=404)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def admin_delete(request, pk):
    try:
        user = User.objects.get(pk=pk)
        if user.is_superadmin:
            return Response({"error": "Неможливо видалити супер-адміна."}, status=403)
        user.delete()
        return Response({"success": True})
    except User.DoesNotExist:
        return Response({"error": "Admin not found."}, status=404)


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
    if not check_password(password, user.password):
        return Response({'success': False, 'error': 'Невірний email або пароль'}, status=401)
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'is_active': user.is_active,
            'is_superadmin': user.is_superadmin,
        }
    })


# ===== STUDENTS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def students_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not (name and email and password):
            return Response({'error': 'Всі поля обовʼязкові!'}, status=400)
        if len(password) < 6:
            return Response({'error': 'Пароль має бути не менше 6 символів!'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email вже існує.'}, status=400)
        user = User.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            is_active=True,
            is_superadmin=False,
            role='student'
        )
        return Response({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active
        }, status=201)

    # --- Ось тут має бути визначення students!
    students = User.objects.filter(role='student')
    return Response([{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "is_active": u.is_active
    } for u in students])

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def student_detail(request, pk):
    try:
        student = User.objects.get(id=pk, role='student')
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({
            'id': student.id,
            'email': student.email,
            'name': student.name,
            'role': student.role,
            'is_active': student.is_active
        })
    if request.method == 'PUT':
        student.name = request.data.get('name', student.name)
        student.email = request.data.get('email', student.email)
        is_active = request.data.get('is_active', None)
        if is_active is not None:
            # Безпечне приведення типу!
            if isinstance(is_active, bool):
                student.is_active = is_active
            elif isinstance(is_active, str):
                student.is_active = is_active.lower() in ['true', '1', 'yes']
            elif isinstance(is_active, int):
                student.is_active = is_active == 1
            else:
                student.is_active = bool(is_active)
        student.save()
        return Response({'success': True, 'student': {
            'id': student.id,
            'name': student.name,
            'email': student.email,
            'is_active': student.is_active
        }})
    if request.method == 'DELETE':
        student.delete()
        return Response({'success': True})


# ===== GROUPS =====

@api_view(['POST'])
@permission_classes([AllowAny])
def group_add_students(request, pk):
    """Додати студентів до групи"""
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)

    student_ids = request.data.get('student_ids', [])

    if not student_ids:
        return Response({'success': False, 'error': 'Не вказано студентів'}, status=400)

    added_count = 0
    for student_id in student_ids:
        try:
            student = User.objects.get(id=student_id, role='student')
            if not GroupStudent.objects.filter(group=group, student=student).exists():
                GroupStudent.objects.create(group=group, student=student)
                added_count += 1
        except User.DoesNotExist:
            continue

    return Response({
        'success': True,
        'message': f'Додано {added_count} студентів'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def group_remove_student(request, pk):
    """Видалити студента з групи"""
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)

    student_id = request.data.get('student_id')

    if not student_id:
        return Response({'success': False, 'error': 'Не вказано студента'}, status=400)

    try:
        student = User.objects.get(id=student_id, role='student')
        GroupStudent.objects.filter(group=group, student=student).delete()
        return Response({'success': True, 'message': 'Студента видалено з групи'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)


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
        return Response({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'color': group.color,
                'schedule': group.schedule,
                'created_at': group.created_at,
                'students': []
            }
        }, status=201)

    groups = Group.objects.all()
    result = []
    for group in groups:
        group_students = GroupStudent.objects.filter(group=group).select_related('student')
        students_data = [{
            'id': gs.student.id,
            'name': gs.student.name,
            'email': gs.student.email
        } for gs in group_students]

        result.append({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'color': group.color,
            'schedule': group.schedule,
            'created_at': group.created_at,
            'students': students_data
        })

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def group_detail(request, pk):
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)

    if request.method == 'GET':
        group_students = GroupStudent.objects.filter(group=group).select_related('student')
        students_data = [{
            'id': gs.student.id,
            'name': gs.student.name,
            'email': gs.student.email
        } for gs in group_students]

        return Response({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'color': group.color,
            'schedule': group.schedule,
            'created_at': group.created_at,
            'students': students_data
        })

    if request.method == 'PUT':
        group.name = request.data.get('name', group.name)
        group.description = request.data.get('description', group.description)
        group.color = request.data.get('color', group.color)
        group.schedule = request.data.get('schedule', group.schedule)
        group.save()

        group_students = GroupStudent.objects.filter(group=group).select_related('student')
        students_data = [{
            'id': gs.student.id,
            'name': gs.student.name,
            'email': gs.student.email
        } for gs in group_students]

        return Response({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'color': group.color,
                'schedule': group.schedule,
                'students': students_data
            }
        })

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
        return Response(
            [{'id': gs.student.id, 'email': gs.student.email, 'name': gs.student.name, 'role': gs.student.role} for gs
             in students])
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
        subject = Subject.objects.create(name=name, short_name=short_name,
                                         description=request.data.get('description', ''),
                                         color=request.data.get('color', '#7c3aed'))
        return Response(
            {'success': True, 'subject': {'id': subject.id, 'name': subject.name, 'short_name': subject.short_name}},
            status=201)
    subjects = Subject.objects.all()
    return Response(
        [{'id': s.id, 'name': s.name, 'short_name': s.short_name, 'description': s.description, 'color': s.color} for s
         in subjects])


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def subject_detail(request, pk):
    try:
        subject = Subject.objects.get(id=pk)
    except Subject.DoesNotExist:
        return Response({'success': False, 'error': 'Предмет не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': subject.id, 'name': subject.name, 'short_name': subject.short_name,
                         'description': subject.description, 'color': subject.color})
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
@permission_classes([AllowAny])
def lessons_list(request):
    if request.method == 'POST':
        # Валідація обов'язкових полів
        if not request.data.get('title'):
            return Response({
                'success': False,
                'error': 'Введіть тему уроку'
            }, status=400)

        if not request.data.get('group_id'):
            return Response({
                'success': False,
                'error': 'Оберіть групу'
            }, status=400)

        if not request.data.get('date'):
            return Response({
                'success': False,
                'error': 'Оберіть дату'
            }, status=400)

        # Валідація дати
        from datetime import datetime, date
        try:
            lesson_date = datetime.strptime(request.data.get('date'), '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'success': False,
                'error': 'Неправильний формат дати'
            }, status=400)

        today = date.today()

        if lesson_date < today:
            return Response({
                'success': False,
                'error': 'Не можна планувати урок на минулу дату'
            }, status=400)

        # Валідація часу
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        if not start_time or not end_time:
            return Response({
                'success': False,
                'error': 'Вкажіть час початку та кінця уроку'
            }, status=400)

        if start_time >= end_time:
            return Response({
                'success': False,
                'error': 'Час початку повинен бути раніше за час кінця'
            }, status=400)

        # Створення уроку
        lesson = Lesson.objects.create(
            title=request.data.get('title'),
            description=request.data.get('description', ''),
            date=lesson_date,
            start_time=start_time,
            end_time=end_time,
            meeting_link=request.data.get('meeting_link', ''),
            status='scheduled',
        )

        # Додаємо subject якщо передано
        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                lesson.subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        # Додаємо group
        try:
            lesson.group = Group.objects.get(id=request.data.get('group_id'))
        except Group.DoesNotExist:
            lesson.delete()
            return Response({
                'success': False,
                'error': 'Група не знайдена'
            }, status=400)

        lesson.save()

        return Response({
            'success': True,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'date': lesson.date.isoformat(),
                'start_time': lesson.start_time,
                'end_time': lesson.end_time,
                'meeting_link': lesson.meeting_link,
            }
        }, status=201)

    # GET - повертаємо всі уроки
    lessons = Lesson.objects.select_related('subject', 'group').all().order_by('-date', '-start_time')
    result = []

    for lesson in lessons:
        lesson_data = {
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'date': lesson.date.isoformat(),
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'meeting_link': lesson.meeting_link or '',
            'status': lesson.status,
            'subject': None,
            'group': None,
        }

        if lesson.subject:
            lesson_data['subject'] = {
                'id': lesson.subject.id,
                'name': lesson.subject.name,
                'short_name': lesson.subject.short_name,
                'color': lesson.subject.color,
            }

        if lesson.group:
            lesson_data['group'] = {
                'id': lesson.group.id,
                'name': lesson.group.name,
                'color': lesson.group.color,
            }

        result.append(lesson_data)

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def lesson_detail(request, pk):
    try:
        lesson = Lesson.objects.select_related('subject', 'group').get(id=pk)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдено'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'date': lesson.date.isoformat(),
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'meeting_link': lesson.meeting_link or '',
            'status': lesson.status,
            'subject': {
                'id': lesson.subject.id,
                'name': lesson.subject.name,
                'short_name': lesson.subject.short_name,
                'color': lesson.subject.color,
            } if lesson.subject else None,
            'group': {
                'id': lesson.group.id,
                'name': lesson.group.name,
                'color': lesson.group.color,
            } if lesson.group else None,
        })

    if request.method == 'PUT':
        lesson.title = request.data.get('title', lesson.title)
        lesson.description = request.data.get('description', lesson.description)
        lesson.meeting_link = request.data.get('meeting_link', lesson.meeting_link)

        if request.data.get('date'):
            from datetime import datetime
            try:
                lesson.date = datetime.strptime(request.data.get('date'), '%Y-%m-%d').date()
            except ValueError:
                pass

        lesson.start_time = request.data.get('start_time', lesson.start_time)
        lesson.end_time = request.data.get('end_time', lesson.end_time)
        lesson.status = request.data.get('status', lesson.status)

        # Оновлюємо subject
        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                lesson.subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        # Оновлюємо group
        group_id = request.data.get('group_id')
        if group_id:
            try:
                lesson.group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        lesson.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        lesson.delete()
        return Response({'success': True})


@api_view(['GET', 'PUT', 'DELETE'])
def lesson_detail(request, pk):
    try:
        lesson = Lesson.objects.get(id=pk)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдений'}, status=404)
    if request.method == 'GET':
        return Response(
            {'id': lesson.id, 'title': lesson.title, 'description': lesson.description, 'status': lesson.status})
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
        return Response(
            [{'id': g.id, 'student': g.student.name, 'grade': g.grade, 'comment': g.comment} for g in grades])
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдений'}, status=404)


# ===== TASKS =====
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def task_detail(request, pk):
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'due_date': task.due_date,
            'status': task.status,
            'created_at': task.created_at
        })

    if request.method == 'PUT':
        task.title = request.data.get('title', task.title)
        task.description = request.data.get('description', task.description)
        task.type = request.data.get('type', task.type)
        task.due_date = request.data.get('due_date', task.due_date)
        task.max_grade = request.data.get('max_grade', task.max_grade)

        # Оновлюємо group
        group_id = request.data.get('group_id')
        if group_id:
            try:
                task.group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        # Оновлюємо subject
        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                task.subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        task.save()
        return Response({'success': True})

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def task_detail(request, pk):
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'due_date': task.due_date,
            'created_at': task.created_at
        })

    if request.method == 'PUT':
        task.title = request.data.get('title', task.title)
        task.description = request.data.get('description', task.description)
        task.type = request.data.get('type', task.type)
        task.due_date = request.data.get('due_date', task.due_date)
        task.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        task.delete()
        return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def tasks_list(request):
    if request.method == 'POST':
        # POST код залишається без змін
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва завдання обов\'язкова'}, status=400)

        due_date = request.data.get('due_date')

        # Валідація дати
        if due_date:
            from datetime import datetime
            try:
                due_date_obj = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                today = datetime.now().date()
                if due_date_obj.date() < today:
                    return Response({
                        'success': False,
                        'error': 'Не можна вказувати дату раніше поточного дня'
                    }, status=400)
            except:
                pass

        # Отримуємо group і subject
        group = None
        subject = None

        group_id = request.data.get('group_id')
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        task = Task.objects.create(
            title=title,
            description=request.data.get('description', ''),
            type=request.data.get('type', 'homework'),
            due_date=due_date,
            max_grade=request.data.get('max_grade', 100),
            group=group,
            subject=subject
        )

        return Response({
            'success': True,
            'task': {
                'id': task.id,
                'title': task.title,
                'type': task.type,
                'max_grade': task.max_grade,
                'due_date': task.due_date,
                'group': {'id': group.id, 'name': group.name, 'color': group.color} if group else None,
                'subject': {'id': subject.id, 'name': subject.name, 'short_name': subject.short_name,
                            'color': subject.color} if subject else None,
            }
        }, status=201)

    # GET - повертаємо всі завдання з повною інформацією
    tasks = Task.objects.select_related('subject', 'group').all()
    result = []

    for task in tasks:
        task_data = {
            'id': task.id,
            'title': task.title,
            'type': task.type,
            'description': task.description,
            'due_date': task.due_date,
            'max_grade': task.max_grade,
            'created_at': task.created_at,
            'subject': None,
            'group': None
        }

        # Додаємо subject якщо є
        if task.subject:
            task_data['subject'] = {
                'id': task.subject.id,
                'name': task.subject.name,
                'short_name': task.subject.short_name,
                'color': task.subject.color
            }

        # Додаємо group якщо є
        if task.group:
            task_data['group'] = {
                'id': task.group.id,
                'name': task.group.name,
                'color': task.group.color
            }

        result.append(task_data)

    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def tasks_bulk_create(request):
    """Масове створення завдань для кількох груп"""
    title = request.data.get('title', '')
    description = request.data.get('description', '')
    task_type = request.data.get('type', 'homework')
    due_date = request.data.get('due_date')
    max_grade = request.data.get('max_grade', 100)
    group_ids = request.data.get('group_ids', [])
    subject_id = request.data.get('subject_id')

    if not title:
        return Response({'success': False, 'error': 'Назва завдання обов\'язкова'}, status=400)

    if not group_ids or len(group_ids) == 0:
        return Response({'success': False, 'error': 'Оберіть хоча б одну групу'}, status=400)

    # Валідація дати
    if due_date:
        from datetime import datetime, date
        try:
            due_date_obj = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            today = datetime.now().date()
            if due_date_obj.date() < today:
                return Response({
                    'success': False,
                    'error': 'Не можна вказувати дату раніше поточного дня'
                }, status=400)
        except:
            pass

    created_tasks = []

    for group_id in group_ids:
        try:
            group = Group.objects.get(id=group_id)
            subject = None
            if subject_id:
                try:
                    subject = Subject.objects.get(id=subject_id)
                except Subject.DoesNotExist:
                    pass

            task = Task.objects.create(
                title=title,
                description=description,
                type=task_type,
                due_date=due_date,
                max_grade=max_grade,
                group=group,
                subject=subject
            )
            created_tasks.append({
                'id': task.id,
                'title': task.title,
                'group': group.name
            })
        except Group.DoesNotExist:
            continue

    return Response({
        'success': True,
        'message': f'Створено {len(created_tasks)} завдань',
        'tasks': created_tasks
    }, status=201)

@api_view(['GET'])
def task_submissions(request, pk):
    try:
        task = Task.objects.get(id=pk)
        submissions = task.submissions.all()
        return Response(
            [{'id': s.id, 'student': s.student.name, 'status': s.status, 'grade': s.grade} for s in submissions])
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)


@api_view(['POST'])
def grade_submission(request, pk):
    return Response({'success': True})


# ===== GRADES & ATTENDANCE =====

@api_view(['GET'])
def grades_list(request):
    grades = LessonGrade.objects.all()
    return Response(
        [{'id': g.id, 'student': g.student.name, 'lesson': g.lesson.title, 'grade': g.grade} for g in grades])


# ===== ATTENDANCE =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def attendance_list(request):
    if request.method == 'POST':
        # Валідація обов'язкових полів
        if not request.data.get('lesson_id'):
            return Response({
                'success': False,
                'error': 'Вкажіть урок'
            }, status=400)

        if not request.data.get('user_id'):
            return Response({
                'success': False,
                'error': 'Вкажіть студента'
            }, status=400)

        # Перевірка чи урок існує
        try:
            lesson = Lesson.objects.get(id=request.data.get('lesson_id'))
        except Lesson.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Урок не знайдено'
            }, status=400)

        # Перевірка чи студент існує
        try:
            user = User.objects.get(id=request.data.get('user_id'))
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Студента не знайдено'
            }, status=400)

        # Перевірка чи запис вже існує
        existing = Attendance.objects.filter(
            lesson=lesson,
            user=user
        ).first()

        if existing:
            # Оновлюємо існуючий запис
            existing.status = request.data.get('status', existing.status)
            existing.notes = request.data.get('notes', existing.notes)
            existing.save()

            return Response({
                'success': True,
                'attendance': {
                    'id': existing.id,
                    'status': existing.status,
                }
            })

        # Створюємо новий запис
        attendance = Attendance.objects.create(
            lesson=lesson,
            user=user,
            status=request.data.get('status', 'present'),
            notes=request.data.get('notes', ''),
        )

        return Response({
            'success': True,
            'attendance': {
                'id': attendance.id,
                'status': attendance.status,
            }
        }, status=201)

    # GET - повертаємо всі записи
    attendance_records = Attendance.objects.select_related('lesson', 'user', 'lesson__group', 'lesson__subject').all()
    result = []

    for record in attendance_records:
        result.append({
            'id': record.id,
            'status': record.status,
            'notes': record.notes or '',
            'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') else None,
            'lesson': {
                'id': record.lesson.id,
                'title': record.lesson.title,
                'date': record.lesson.date.isoformat(),
                'start_time': record.lesson.start_time,
                'end_time': record.lesson.end_time,
                'group': {
                    'id': record.lesson.group.id,
                    'name': record.lesson.group.name,
                    'color': record.lesson.group.color,
                } if record.lesson.group else None,
                'subject': {
                    'id': record.lesson.subject.id,
                    'name': record.lesson.subject.name,
                } if record.lesson.subject else None,
            },
            'user': {
                'id': record.user.id,
                'name': record.user.name,
                'email': record.user.email,
            },
        })

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def attendance_detail(request, pk):
    try:
        attendance = Attendance.objects.select_related('lesson', 'user').get(id=pk)
    except Attendance.DoesNotExist:
        return Response({'success': False, 'error': 'Запис не знайдено'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': attendance.id,
            'status': attendance.status,
            'notes': attendance.notes or '',
            'lesson_id': attendance.lesson.id,
            'user_id': attendance.user.id,
        })

    if request.method == 'PUT':
        attendance.status = request.data.get('status', attendance.status)
        attendance.notes = request.data.get('notes', attendance.notes)
        attendance.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        attendance.delete()
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([AllowAny])
def attendance_by_lesson(request):
    """
    GET /api/attendance/?lesson_id=XXX
    Повернути {lesson, students: [user, attendance]}
    """
    lesson_id = request.query_params.get('lesson_id')
    if not lesson_id:
        return Response({'success': False, 'error': 'Потрібен lesson_id'}, status=400)

    try:
        lesson = Lesson.objects.select_related('group').get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдено'}, status=404)

    students = User.objects.filter(group=lesson.group, role='student')
    records = Attendance.objects.filter(lesson=lesson)
    attendance_dict = {a.user_id: a for a in records}

    result = []
    for student in students:
        attendance_item = attendance_dict.get(student.id)
        result.append({
            'user': {
                'id': student.id,
                'name': student.name,
                'email': student.email,
                'avatar_url': student.avatar_url or '',
            },
            'attendance': {
                'id': attendance_item.id if attendance_item else None,
                'status': attendance_item.status if attendance_item else 'present',
                'notes': attendance_item.notes if attendance_item else '',
            } if attendance_item else None,
        })

    return Response({
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'date': lesson.date,
            'group': {
                'id': lesson.group.id,
                'name': lesson.group.name,
                'color': lesson.group.color,
            }
        },
        'students': result,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def attendance_bulk_update(request):
    """
    POST масивом [{user_id, lesson_id, status}]
    """
    records = request.data.get('attendance')
    if not isinstance(records, list):
        return Response({'success': False, 'error': 'attendance має бути списком'}, status=400)

    updated, created = 0, 0
    for rec in records:
        user_id = rec.get('user_id')
        lesson_id = rec.get('lesson_id')
        status = rec.get('status', 'present')
        if not (user_id and lesson_id and status):
            continue
        att, is_new = Attendance.objects.update_or_create(
            user_id=user_id,
            lesson_id=lesson_id,
            defaults={'status': status}
        )
        if is_new:
            created += 1
        else:
            updated += 1

    return Response({'success': True, 'created': created, 'updated': updated})

# ===== INVOICES =====

@api_view(['GET'])
def invoices_list(request):
    invoices = Invoice.objects.all()
    return Response(
        [{'id': i.id, 'student': i.student.name, 'amount': str(i.amount), 'status': i.status} for i in invoices])


@api_view(['GET'])
def invoices_history(request):
    invoices = Invoice.objects.all()
    return Response([{'id': i.id, 'student': i.student.name, 'amount': str(i.amount), 'paid_amount': str(i.paid_amount),
                      'status': i.status} for i in invoices])


# ===== ADMIN & STATS =====

@api_view(['GET'])
def admin_stats(request):
    return Response(
        {'students': User.objects.filter(role='student').count(), 'admins': User.objects.filter(role='admin').count(),
         'groups': Group.objects.count()})


@api_view(['GET'])
def leaderboard(request):
    points = StudentPoint.objects.values('student__name').annotate(total=sum('points')).order_by('-total')[:10]
    return Response(list(points))


# ===== NEWS =====


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def news_list(request):
    if request.method == 'POST':
        # --- Валідація та отримання значень ---
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        category = request.data.get('category', '').strip()
        image_url = request.data.get('image_url', '')
        video_url = request.data.get('video_url', '')
        link = request.data.get('link', '')

        # ГОЛОВНЕ! каст bool для is_published (приходить як "true"/"false" — string)
        is_published_raw = request.data.get('is_published', 'false')
        is_published = True if str(is_published_raw).lower() == 'true' else False

        if not title or not content or not category:
            return Response({'success': False, 'error': 'Заповніть усі обовʼязкові поля'}, status=400)

        news = News.objects.create(
            title=title,
            content=content,
            category=category,
            is_published=is_published,
            published_at=timezone.now() if is_published else None,
            image_url=image_url,
            video_url=video_url,
            link=link,
        )
        return Response({'success': True, 'news_id': news.id}, status=201)

    # --- GET метод: список новин ---
    data = []
    for n in News.objects.order_by("-created_at"):
        data.append({
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'created_at': n.created_at,
            'is_published': n.is_published,
            'category': n.category,
            'image_url': n.image_url,
            'video_url': n.video_url,
            'link': n.link,
            'views_count': n.views_count,
        })
    return Response(data)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def news_detail(request, pk):
    try:
        news = News.objects.get(id=pk)
    except News.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)

    if request.method == 'GET':
        # +1 до views
        news.views_count += 1
        news.save()
        return Response({
            'id': news.id,
            'title': news.title,
            'content': news.content,
            'created_at': news.created_at,
            'is_published': news.is_published,
            'category': news.category,
            'image_url': news.image_url,
            'video_url': news.video_url,
            'link': news.link,
            'views_count': news.views_count,
        })
    if request.method == 'PUT':
        news.title = request.data.get('title', news.title)
        news.content = request.data.get('content', news.content)
        news.category = request.data.get('category', news.category)
        news.is_published = request.data.get('is_published', news.is_published)
        news.image_url = request.data.get('image_url', news.image_url)
        news.video_url = request.data.get('video_url', news.video_url)
        news.link = request.data.get('link', news.link)
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
        extra_news = ExtraNews.objects.create(title=title, description=request.data.get('description', ''),
                                              media_type=request.data.get('media_type'),
                                              media_url=request.data.get('media_url'))
        return Response({'success': True, 'news': {'id': extra_news.id, 'title': extra_news.title}}, status=201)
    extra_news_list_obj = ExtraNews.objects.filter(is_active=True)
    return Response([{'id': n.id, 'title': n.title, 'media_type': n.media_type, 'media_url': n.media_url} for n in
                     extra_news_list_obj])


@api_view(['GET', 'PUT', 'DELETE'])
def extra_news_detail(request, pk):
    try:
        extra_news = ExtraNews.objects.get(id=pk)
    except ExtraNews.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': extra_news.id, 'title': extra_news.title, 'description': extra_news.description,
                         'media_type': extra_news.media_type})
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
    return Response(
        [{'id': m.id, 'sender': m.sender.name, 'content': m.content, 'created_at': m.created_at} for m in messages])


# ===== POLLS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def polls_list(request):
    if request.method == 'POST':
        title = request.data.get('title')
        options = request.data.get('options', [])
        target_type = request.data.get('targetType', 'all')
        group_ids = request.data.get('groupIds', [])
        is_anonymous = request.data.get('isAnonymous', False)
        is_multiple_choice = request.data.get('isMultipleChoice', False)
        ends_at = request.data.get('endsAt')

        # Валідація
        if not title or len(options) < 2 or not ends_at:
            return Response({'success': False, 'error': 'Перевірте всі обовʼязкові поля'}, status=400)
        # Дата не раніше сьогодні
        if ends_at < str(date.today()):
            return Response({'success': False, 'error': 'Дата закриття некоректна'}, status=400)

        poll = Poll.objects.create(
            title=title,
            description=request.data.get('description',''),
            target_type=target_type,
            is_anonymous=is_anonymous,
            is_multiple_choice=is_multiple_choice,
            ends_at=ends_at
        )
        # Окремо додаємо групи
        if target_type == "group" and isinstance(group_ids, list):
            for gid in group_ids:
                try:
                    g = Group.objects.get(id=gid)
                    poll.target_group = g
                    poll.save()
                except:
                    pass

        for o in options:
            PollOption.objects.create(poll=poll, text=o['text'])

        return Response({'success': True, 'pollId': poll.id})

    # GET — список опитувань (простий респонс, додай потрібні поля)
    result = []
    for poll in Poll.objects.all().order_by('-created_at'):
        result.append({
            'id': poll.id,
            'title': poll.title,
            'description': poll.description,
            'isAnonymous': poll.is_anonymous,
            'isMultipleChoice': poll.is_multiple_choice,
            'targetType': poll.target_type,
            'targetGroupId': poll.target_group_id,
            'targetGroupName': poll.target_group.name if poll.target_group else 'Всі учні',
            'options': [{'id': po.id, 'text': po.text, 'votes': po.votes.count() if hasattr(po, 'votes') else 0} for po in poll.options.all()],
            'endsAt': poll.ends_at.isoformat(),
            'createdAt': poll.created_at.isoformat() if poll.created_at else '',
            'status': poll.status,
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def poll_detail(request, pk):
    """
    Детальна інформація про опитування + всі варіанти і кількість голосів
    """
    try:
        poll = Poll.objects.select_related('target_group').get(id=pk)
        options = poll.options.all()

        options_data = []
        for option in options:
            votes_count = option.votes.count() if hasattr(option, 'votes') else 0
            options_data.append({
                'id': option.id,
                'text': option.text,
                'votes': votes_count,
            })
        return Response({
            'id': poll.id,
            'title': poll.title,
            'description': poll.description,
            'isAnonymous': poll.is_anonymous,
            'isMultipleChoice': poll.is_multiple_choice,
            'targetType': poll.target_type,
            'targetGroupId': poll.target_group_id,
            'targetGroupName': poll.target_group.name if poll.target_group else "Всі учні",
            'status': poll.status,
            'options': options_data,
            'endsAt': poll.ends_at.isoformat(),
            'createdAt': poll.created_at.isoformat() if poll.created_at else '',
        })
    except Poll.DoesNotExist:
        return Response({'success': False, 'error': 'Опитування не знайдене'}, status=404)

@api_view(['POST'])
@permission_classes([AllowAny])
def poll_vote(request, pk):
    """
    Додати голосування: pk - option.id, student_id в тілі
    """
    try:
        option = PollOption.objects.get(id=pk)
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'success': False, 'error': 'Student ID обов\'язковий'}, status=400)
        student = User.objects.get(id=student_id)

        # Захист від подвійного голосу:
        if PollVote.objects.filter(option=option, student=student).exists():
            return Response({'success': False, 'error': 'Ви вже голосували за цей варіант'}, status=400)

        vote = PollVote.objects.create(option=option, student=student)
        return Response({'success': True, 'vote': {'id': vote.id}}, status=201)
    except (PollOption.DoesNotExist, User.DoesNotExist):
        return Response({'success': False, 'error': 'Not found (option or student)'}, status=404)

# ===== COURSES =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def courses_list(request):
    if request.method == 'POST':
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва курсу обов\'язкова'}, status=400)

        group = None
        subject = None

        group_id = request.data.get('group_id')
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        course = Course.objects.create(
            title=title,
            description=request.data.get('description', ''),
            group=group,
            subject=subject,
            thumbnail=request.data.get('thumbnail', ''),
            is_published=request.data.get('is_published', False)
        )

        return Response({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'is_published': course.is_published
            }
        }, status=201)

    # GET
    courses = Course.objects.select_related('group', 'subject').all()
    result = []

    for course in courses:
        course_data = {
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'thumbnail': course.thumbnail,
            'is_published': course.is_published,
            'created_at': course.created_at,
            'group': None,
            'subject': None,
            'materials_count': course.materials.count() if hasattr(course, 'materials') else 0,
            'tests_count': course.tests.count() if hasattr(course, 'tests') else 0,
        }

        if course.group:
            course_data['group'] = {
                'id': course.group.id,
                'name': course.group.name,
                'color': course.group.color
            }

        if course.subject:
            course_data['subject'] = {
                'id': course.subject.id,
                'name': course.subject.name,
                'short_name': course.subject.short_name,
                'color': course.subject.color
            }

        result.append(course_data)

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def course_detail(request, pk):
    try:
        course = Course.objects.select_related('group', 'subject').get(id=pk)
    except Course.DoesNotExist:
        return Response({'success': False, 'error': 'Курс не знайдений'}, status=404)

    if request.method == 'GET':
        # Отримуємо матеріали та тести
        materials = course.materials.all()
        tests = course.tests.prefetch_related('questions__options').all()

        materials_data = [{
            'id': m.id,
            'title': m.title,
            'type': m.type,
            'url': m.url,
            'order': m.order,
            'duration': m.duration,
            'is_required': m.is_required
        } for m in materials]

        tests_data = []
        for test in tests:
            questions_data = []
            for q in test.questions.all():
                options_data = [{
                    'id': o.id,
                    'text': o.text,
                    'is_correct': o.is_correct,
                    'order': o.order
                } for o in q.options.all()]

                questions_data.append({
                    'id': q.id,
                    'question': q.question,
                    'type': q.type,
                    'points': q.points,
                    'order': q.order,
                    'options': options_data
                })

            tests_data.append({
                'id': test.id,
                'title': test.title,
                'description': test.description,
                'pass_score': test.pass_score,
                'time_limit': test.time_limit,
                'is_active': test.is_active,
                'questions': questions_data
            })

        return Response({
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'thumbnail': course.thumbnail,
            'is_published': course.is_published,
            'group': {
                'id': course.group.id,
                'name': course.group.name,
                'color': course.group.color
            } if course.group else None,
            'subject': {
                'id': course.subject.id,
                'name': course.subject.name,
                'short_name': course.subject.short_name,
                'color': course.subject.color
            } if course.subject else None,
            'materials': materials_data,
            'tests': tests_data
        })

    if request.method == 'PUT':
        course.title = request.data.get('title', course.title)
        course.description = request.data.get('description', course.description)
        course.thumbnail = request.data.get('thumbnail', course.thumbnail)
        course.is_published = request.data.get('is_published', course.is_published)

        group_id = request.data.get('group_id')
        if group_id:
            try:
                course.group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        subject_id = request.data.get('subject_id')
        if subject_id:
            try:
                course.subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass

        course.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        course.delete()
        return Response({'success': True})


@api_view(['POST'])
@permission_classes([AllowAny])
def course_add_material(request, pk):
    """Додати матеріал до курсу"""
    try:
        course = Course.objects.get(id=pk)
    except Course.DoesNotExist:
        return Response({'success': False, 'error': 'Курс не знайдений'}, status=404)

    title = request.data.get('title', '')
    material_type = request.data.get('type', 'video')
    url = request.data.get('url', '')

    if not title or not url:
        return Response({'success': False, 'error': 'Назва та URL обов\'язкові'}, status=400)

    # Отримуємо максимальний order
    max_order = CourseMaterial.objects.filter(course=course).aggregate(
        models.Max('order')
    )['order__max'] or 0

    material = CourseMaterial.objects.create(
        course=course,
        title=title,
        type=material_type,
        url=url,
        order=max_order + 1,
        duration=request.data.get('duration'),
        is_required=request.data.get('is_required', True)
    )

    return Response({
        'success': True,
        'material': {
            'id': material.id,
            'title': material.title,
            'type': material.type,
            'url': material.url
        }
    }, status=201)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def course_remove_material(request, course_pk, material_pk):
    """Видалити матеріал з курсу"""
    try:
        material = CourseMaterial.objects.get(id=material_pk, course_id=course_pk)
        material.delete()
        return Response({'success': True})
    except CourseMaterial.DoesNotExist:
        return Response({'success': False, 'error': 'Матеріал не знайдений'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def course_add_test(request, pk):
    """Додати тест до курсу"""
    try:
        course = Course.objects.get(id=pk)
    except Course.DoesNotExist:
        return Response({'success': False, 'error': 'Курс не знайдений'}, status=404)

    title = request.data.get('title', '')
    if not title:
        return Response({'success': False, 'error': 'Назва тесту обов\'язкова'}, status=400)

    test = CourseTest.objects.create(
        course=course,
        title=title,
        description=request.data.get('description', ''),
        pass_score=request.data.get('pass_score', 70),
        time_limit=request.data.get('time_limit')
    )

    # Додаємо питання якщо є
    questions_data = request.data.get('questions', [])
    for q_data in questions_data:
        question = TestQuestion.objects.create(
            test=test,
            question=q_data.get('question', ''),
            type=q_data.get('type', 'single'),
            points=q_data.get('points', 1),
            order=q_data.get('order', 0)
        )

        # Додаємо варіанти відповідей
        options_data = q_data.get('options', [])
        for o_data in options_data:
            QuestionOption.objects.create(
                question=question,
                text=o_data.get('text', ''),
                is_correct=o_data.get('is_correct', False),
                order=o_data.get('order', 0)
            )

    return Response({
        'success': True,
        'test': {
            'id': test.id,
            'title': test.title
        }
    }, status=201)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def course_remove_test(request, course_pk, test_pk):
    """Видалити тест з курсу"""
    try:
        test = CourseTest.objects.get(id=test_pk, course_id=course_pk)
        test.delete()
        return Response({'success': True})
    except CourseTest.DoesNotExist:
        return Response({'success': False, 'error': 'Тест не знайдений'}, status=404)
# ===== TEAMS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def teams_list(request):
    if request.method == 'POST':
        name = request.data.get('name', '')
        if not name:
            return Response({'success': False, 'error': 'Назва команди обов\'язкова'}, status=400)
        team = Team.objects.create(name=name, description=request.data.get('description', ''),
                                   color=request.data.get('color', '#FF9A00'))
        return Response({'success': True, 'team': {'id': team.id, 'name': team.name}}, status=201)

    # GET - повертаємо команди зі студентами
    teams = Team.objects.all()
    result = []
    for team in teams:
        # Отримуємо студентів команди
        team_members = TeamMember.objects.filter(team=team).select_related('student')
        members_data = [{
            'id': tm.student.id,
            'name': tm.student.name,
            'email': tm.student.email
        } for tm in team_members]

        result.append({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'color': team.color,
            'total_points': team.total_points,
            'created_at': team.created_at,
            'members': members_data
        })

    return Response(result)

    @api_view(['POST'])
    @permission_classes([AllowAny])
    def team_add_members(request, pk):
        """Додати студентів до команди"""
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)

        student_ids = request.data.get('student_ids', [])

        if not student_ids:
            return Response({'success': False, 'error': 'Не вказано студентів'}, status=400)

        added_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id, role='student')

                # Перевіряємо чи студент вже в ІНШІЙ команді
                existing_membership = TeamMember.objects.filter(student=student).first()
                if existing_membership:
                    if existing_membership.team.id == team.id:
                        errors.append(f'{student.name} вже в цій команді')
                    else:
                        errors.append(f'{student.name} вже в команді "{existing_membership.team.name}"')
                    continue

                # Додаємо студента до команди
                TeamMember.objects.create(team=team, student=student)
                added_count += 1

            except User.DoesNotExist:
                continue

        message = f'Додано {added_count} студентів'
        if errors:
            message += '. Помилки: ' + '; '.join(errors)

        return Response({
            'success': True,
            'message': message,
            'added': added_count,
            'errors': errors
        })

    @api_view(['POST'])
    @permission_classes([AllowAny])
    def team_remove_member(request, pk):
        """Видалити студента з команди"""
        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)

        student_id = request.data.get('student_id')

        if not student_id:
            return Response({'success': False, 'error': 'Не вказано студента'}, status=400)

        try:
            student = User.objects.get(id=student_id, role='student')
            TeamMember.objects.filter(team=team, student=student).delete()
            return Response({'success': True, 'message': 'Студента видалено з команди'})
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)

    # GET - повертаємо команди зі студентами
    teams = Team.objects.all()
    result = []
    for team in teams:
        # Отримуємо студентів команди
        team_members = TeamMember.objects.filter(team=team).select_related('student')
        members_data = [{
            'id': tm.student.id,
            'name': tm.student.name,
            'email': tm.student.email
        } for tm in team_members]

        result.append({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'color': team.color,
            'total_points': team.total_points,
            'created_at': team.created_at,
            'members': members_data  # ✅ Додаємо список студентів
        })

    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def team_add_members(request, pk):
    """Додати студентів до команди"""
    try:
        team = Team.objects.get(id=pk)
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)

    student_ids = request.data.get('student_ids', [])

    if not student_ids:
        return Response({'success': False, 'error': 'Не вказано студентів'}, status=400)

    added_count = 0
    errors = []

    for student_id in student_ids:
        try:
            student = User.objects.get(id=student_id, role='student')

            # Перевіряємо чи студент вже в ІНШІЙ команді
            existing_membership = TeamMember.objects.filter(student=student).first()
            if existing_membership:
                if existing_membership.team.id == team.id:
                    errors.append(f'{student.name} вже в цій команді')
                else:
                    errors.append(f'{student.name} вже в команді "{existing_membership.team.name}"')
                continue

            # Додаємо студента до команди
            TeamMember.objects.create(team=team, student=student)
            added_count += 1

        except User.DoesNotExist:
            continue

    return Response({
        'success': True,
        'message': f'Додано {added_count} студентів',
        'errors': errors
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def team_remove_member(request, pk):
    """Видалити студента з команди"""
    try:
        team = Team.objects.get(id=pk)
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)

    student_id = request.data.get('student_id')

    if not student_id:
        return Response({'success': False, 'error': 'Не вказано студента'}, status=400)

    try:
        student = User.objects.get(id=student_id, role='student')
        TeamMember.objects.filter(team=team, student=student).delete()
        return Response({'success': True, 'message': 'Студента видалено з команди'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)


@api_view(['GET', 'PUT', 'DELETE'])
def team_detail(request, pk):
    try:
        team = Team.objects.get(id=pk)
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)
    if request.method == 'GET':
        return Response(
            {'id': team.id, 'name': team.name, 'description': team.description, 'total_points': team.total_points})
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

        puzzle = Puzzle.objects.create(
            title=title,
            question=question,
            answer=answer,
            hint=request.data.get('hint', ''),
            type=request.data.get('type', 'riddle'),
            difficulty=request.data.get('difficulty', 'medium'),
            points=request.data.get('points', 10)
        )

        return Response({
            'success': True,
            'puzzle': {
                'id': puzzle.id,
                'title': puzzle.title,
                'question': puzzle.question,
                'hint': puzzle.hint,
                'type': puzzle.type,
                'difficulty': puzzle.difficulty,
                'points': puzzle.points,
                'solved_by': puzzle.solved_by,
                'created_at': puzzle.created_at
            }
        }, status=201)

    # GET - повертаємо всі активні загадки
    puzzles = Puzzle.objects.filter(is_active=True)
    return Response([{
        'id': p.id,
        'title': p.title,
        'question': p.question,
        'hint': p.hint,
        'type': p.type,
        'difficulty': p.difficulty,
        'points': p.points,
        'solved_by': p.solved_by,
        'created_at': p.created_at
    } for p in puzzles])


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def puzzle_detail(request, pk):
    try:
        puzzle = Puzzle.objects.get(id=pk)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': puzzle.id,
            'title': puzzle.title,
            'question': puzzle.question,
            'answer': puzzle.answer,  # Для адміна показуємо відповідь
            'hint': puzzle.hint,
            'type': puzzle.type,
            'difficulty': puzzle.difficulty,
            'points': puzzle.points,
            'solved_by': puzzle.solved_by
        })

    if request.method == 'PUT':
        puzzle.title = request.data.get('title', puzzle.title)
        puzzle.question = request.data.get('question', puzzle.question)
        puzzle.answer = request.data.get('answer', puzzle.answer)
        puzzle.hint = request.data.get('hint', puzzle.hint)
        puzzle.type = request.data.get('type', puzzle.type)
        puzzle.difficulty = request.data.get('difficulty', puzzle.difficulty)
        puzzle.points = request.data.get('points', puzzle.points)
        puzzle.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        puzzle.delete()
        return Response({'success': True})


@api_view(['POST'])
@permission_classes([AllowAny])
def puzzle_answer(request, pk):
    """Перевірка відповіді на загадку"""
    try:
        puzzle = Puzzle.objects.get(id=pk)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)

    answer = request.data.get('answer', '').strip().lower()
    correct_answer = puzzle.answer.strip().lower()

    if answer == correct_answer:
        puzzle.solved_by += 1
        puzzle.save()
        return Response({
            'success': True,
            'correct': True,
            'points': puzzle.points,
            'message': f'Правильно! Ви отримали {puzzle.points} балів!'
        })

    return Response({
        'success': False,
        'correct': False,
        'message': 'Неправильна відповідь. Спробуйте ще раз!'
    }, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def puzzle_answer(request, pk):
    try:
        puzzle = Puzzle.objects.get(id=pk)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)

    answer = request.data.get('answer', '').strip().lower()
    correct_answer = puzzle.answer.strip().lower()

    if answer == correct_answer:
        puzzle.solved_by += 1
        puzzle.save()
        return Response({
            'success': True,
            'correct': True,
            'points': puzzle.points,
            'message': f'Правильно! Ви отримали {puzzle.points} балів!'
        })

    return Response({
        'success': False,
        'correct': False,
        'message': 'Неправильна відповідь. Спробуйте ще раз!'
    }, status=400)


@api_view(['GET'])
def puzzle_detail(request, pk):
    try:
        puzzle = Puzzle.objects.get(id=pk)
        return Response({'id': puzzle.id, 'title': puzzle.title, 'question': puzzle.question, 'hint': puzzle.hint,
                         'difficulty': puzzle.difficulty, 'points': puzzle.points})
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
        material = LearningMaterial.objects.create(title=title, description=request.data.get('description', ''),
                                                   type=request.data.get('type', 'material'))
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
        return Response(
            {'id': material.id, 'title': material.title, 'description': material.description, 'type': material.type})
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
    return Response(
        [{'id': n.id, 'title': n.title, 'message': n.message, 'is_read': n.is_read, 'created_at': n.created_at} for n in
         notifications])


@api_view(['POST'])
def notification_read(request, pk):
    try:
        notification = Notification.objects.get(id=pk)
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'success': False, 'error': 'Сповіщення не знайдено'}, status=404)


# ===== USERS =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def users_list(request):
    if request.method == 'POST':
        # Валідація обов'язкових полів
        required_fields = ['email', 'password', 'role']
        for field in required_fields:
            if not request.data.get(field):
                return Response({
                    'success': False,
                    'error': f'Поле {field} обов\'язкове'
                }, status=400)

        email = request.data.get('email')

        # Перевірка чи email вже існує
        if User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': 'Користувач з таким email вже і��нує'
            }, status=400)

        # Хешування пароля
        from django.contrib.auth.hashers import make_password

        # Створюємо ім'я з surname, name, patronymic
        full_name_parts = []
        if request.data.get('surname'):
            full_name_parts.append(request.data.get('surname'))
        if request.data.get('name'):
            full_name_parts.append(request.data.get('name'))
        if request.data.get('patronymic'):
            full_name_parts.append(request.data.get('patronymic'))

        full_name = ' '.join(full_name_parts) if full_name_parts else request.data.get('name', 'Student')

        # Створення користувача
        user = User.objects.create(
            email=email,
            password=make_password(request.data.get('password')),
            name=full_name,  # Зберігаємо повне ПІБ в одне поле
            phone=request.data.get('phone', ''),
            role=request.data.get('role', 'student'),
            status='active',
            is_active=True,
        )

        # Додаємо групу якщо передано
        group_id = request.data.get('group_id')
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                user.group = group
                user.save()
            except Group.DoesNotExist:
                pass

        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'status': user.status,
            }
        }, status=201)

    # GET - повертаємо всіх користувачів
    users = User.objects.select_related('group').all()
    result = []

    for user in users:
        user_data = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone or '',
            'role': user.role,
            'status': user.status,
            'avatar_url': user.avatar_url or '',
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'group': None,
        }

        if user.group:
            user_data['group'] = {
                'id': user.group.id,
                'name': user.group.name,
                'color': user.group.color,
            }

        result.append(user_data)

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def user_detail(request, pk):
    try:
        user = User.objects.select_related('group').get(id=pk)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Користувача не знайдено'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone or '',
            'role': user.role,
            'status': user.status,
            'avatar_url': user.avatar_url or '',
            'group': {
                'id': user.group.id,
                'name': user.group.name,
                'color': user.group.color,
            } if user.group else None,
        })

    if request.method == 'PUT':
        user.email = request.data.get('email', user.email)

        # Оновлюємо ім'я (може бути повне ПІБ)
        if request.data.get('name'):
            user.name = request.data.get('name')

        user.phone = request.data.get('phone', user.phone)
        user.role = request.data.get('role', user.role)
        user.status = request.data.get('status', user.status)

        # Оновлюємо пароль якщо передано
        if request.data.get('password'):
            from django.contrib.auth.hashers import make_password
            user.password = make_password(request.data.get('password'))

        # Оновлюємо групу
        group_id = request.data.get('group_id')
        if group_id:
            try:
                user.group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass

        user.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        user.delete()
        return Response({'success': True})