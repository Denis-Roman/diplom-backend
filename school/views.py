import os
import json
import datetime
import bcrypt
import jwt
from datetime import timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.utils.dateparse import parse_date
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
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
    Team, TeamMember, Chat, ChatParticipant, ChatMessage, ChatMessageAttachment, Poll,
    PollOption, CourseMaterial, CourseTest, TestQuestion, QuestionOption, PollVote, Course, Puzzle, LearningMaterial,
    TaskSubmission, SubmissionFile, InvoicePaymentReceipt, LearningMaterialAttachment,
    LearningMaterialGroup,
    LearningMaterialFolder,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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


def _effective_role(user) -> str | None:
    if not user:
        return None
    if getattr(user, 'is_superadmin', False):
        return 'superadmin'
    raw_role = getattr(user, 'role', None)
    if raw_role is None:
        return None

    role = str(raw_role).strip().lower()
    if role in ('student', 'user', 'pupil'):
        return 'student'
    if role in ('admin',):
        return 'admin'
    if role in ('superadmin', 'super_admin', 'super-admin'):
        return 'superadmin'
    return role


def _require_roles(request, roles: tuple[str, ...]):
    role = _effective_role(getattr(request, 'user', None))
    if role not in roles:
        return Response({'detail': 'Forbidden'}, status=403)
    return None


def _can_access_user(viewer: User, target: User) -> bool:
    viewer_role = _effective_role(viewer)
    if viewer_role == 'superadmin':
        return True
    if getattr(target, 'is_superadmin', False) or getattr(target, 'role', None) == 'superadmin':
        return False
    if viewer_role == 'admin':
        return True
    return viewer.id == target.id


def _absolute_file_url(request, url: str | None) -> str:
    raw = str(url or '').strip()
    if not raw:
        return ''
    if raw.startswith('http://') or raw.startswith('https://'):
        return raw
    if raw.startswith('/'):
        return request.build_absolute_uri(raw)
    return request.build_absolute_uri(f'/{raw}')


def _can_admin_manage_task(user: User, task: Task) -> bool:
    role = _effective_role(user)
    if role == 'superadmin':
        return True
    if role != 'admin':
        return False
    return getattr(task, 'assigned_admin_id', None) in (None, user.id)


def _scope_tasks_for_role(user: User, queryset):
    role = _effective_role(user)
    if role == 'superadmin':
        return queryset
    if role == 'admin':
        return queryset.filter(models.Q(assigned_admin_id=user.id) | models.Q(assigned_admin_id__isnull=True))
    return queryset.none()


def _parse_admin_target(value):
    if value in (None, '', 'null'):
        return None
    try:
        admin_id = int(value)
    except (TypeError, ValueError):
        return None
    return User.objects.filter(id=admin_id, role='admin').first()


def _redistribute_admin_tasks(source_admin: User, target_admin: User | None = None) -> int:
    tasks = list(Task.objects.filter(assigned_admin_id=source_admin.id).order_by('id'))
    if not tasks:
        return 0

    if target_admin and target_admin.id != source_admin.id:
        Task.objects.filter(id__in=[t.id for t in tasks]).update(assigned_admin=target_admin)
        return len(tasks)

    candidates = list(
        User.objects.filter(role='admin', is_active=True)
        .exclude(id=source_admin.id)
        .order_by('id')
    )
    if not candidates:
        Task.objects.filter(id__in=[t.id for t in tasks]).update(assigned_admin=None)
        return len(tasks)

    load = {
        admin.id: int(
            Task.objects.filter(assigned_admin_id=admin.id).count()
        )
        for admin in candidates
    }

    changed = 0
    for task in tasks:
        target = min(candidates, key=lambda admin: load.get(admin.id, 0))
        task.assigned_admin = target
        task.save(update_fields=['assigned_admin'])
        load[target.id] = load.get(target.id, 0) + 1
        changed += 1
    return changed

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def administrator_detail(request, pk):
    forbidden = _require_roles(request, ('superadmin',))
    if forbidden:
        return forbidden
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

        reassign_to = (
            request.data.get('reassign_to_admin_id')
            if hasattr(request, 'data') else None
        ) or request.query_params.get('reassign_to_admin_id')
        target_admin = _parse_admin_target(reassign_to)
        if reassign_to not in (None, '', 'null') and not target_admin:
            return Response({'error': 'Цільового адміністратора не знайдено'}, status=400)
        if target_admin and target_admin.id == admin.id:
            return Response({'error': 'Неможливо призначити завдання тому ж адміну'}, status=400)

        _redistribute_admin_tasks(admin, target_admin)
        admin.delete()
        return Response({'success': True})

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def news_update(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def news_create(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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


def create_invoice(request):
    """Internal helper used by POST /api/invoices/.

    IMPORTANT: must accept DRF Request (not wrapped by @api_view), otherwise calling it
    from another DRF view will raise AssertionError.
    """

    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden

    students = request.data.get('student_ids', [])
    amount_raw = request.data.get('amount')
    description = (request.data.get('description', '') or '').strip()
    installments_raw = request.data.get('installments', 1)
    due_date_raw = request.data.get('due_date')

    if not isinstance(students, list) or not students:
        return Response({'success': False, 'error': 'Оберіть хоча б одного учня'}, status=400)

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        return Response({'success': False, 'error': 'Некоректна сума'}, status=400)
    if amount <= 0:
        return Response({'success': False, 'error': 'Сума має бути більшою за 0'}, status=400)

    try:
        installments = int(installments_raw)
    except (TypeError, ValueError):
        installments = 1
    if installments < 1:
        installments = 1

    due_date = parse_date(str(due_date_raw or '').strip())
    if not due_date:
        return Response({'success': False, 'error': 'Некоректна дата платежу'}, status=400)

    def _user_registration_date(user: User):
        """Return best-effort registration date (local TZ) for validations.

        We use the maximum of:
        - User.registered_at (DateField)
        - local date of User.created_at (DateTimeField)

        This avoids edge cases around midnight/UTC where created_at/registered_at
        can appear as previous day.
        """

        reg = getattr(user, 'registered_at', None)
        if isinstance(reg, datetime.datetime):
            try:
                reg = timezone.localtime(reg).date()
            except Exception:
                reg = reg.date()
        if not isinstance(reg, datetime.date):
            reg = None

        created_at = getattr(user, 'created_at', None)
        created_date = None
        if isinstance(created_at, datetime.datetime):
            try:
                created_date = timezone.localtime(created_at).date()
            except Exception:
                created_date = created_at.date()

        if reg and created_date:
            return max(reg, created_date)
        return reg or created_date

    # Перевірка дати платежу проти дати реєстрації (важливо для масового виставлення)
    students_qs = User.objects.filter(id__in=students)
    found_ids = set(students_qs.values_list('id', flat=True))
    missing = [sid for sid in students if sid not in found_ids]
    if missing:
        return Response({'success': False, 'error': f'Учні не знайдені: {missing}'}, status=404)

    invalid_students = []
    for student in students_qs:
        reg_date = _user_registration_date(student)
        if reg_date and due_date < reg_date:
            invalid_students.append(
                {
                    'id': student.id,
                    'name': student.name,
                    'email': student.email,
                    'registeredAt': reg_date.isoformat(),
                }
            )

    if invalid_students:
        return Response(
            {
                'success': False,
                'error': 'Дата платежу не може бути раніше дати реєстрації учня',
                'invalidStudents': invalid_students,
            },
            status=400,
        )

    # Створення рахунка для кожного студента
    result = []
    for student in students_qs:
        for i in range(installments):
            current_due = due_date + datetime.timedelta(days=30 * i)
            inv = Invoice.objects.create(
                student=student,
                amount=amount,
                paid_amount=0,
                installments=installments,
                current_installment=i + 1,
                description=description,
                status='pending',
                due_date=current_due,
            )
            Notification.objects.create(
                user=student,
                type='invoice',
                title='Новий рахунок',
                message=f'Вам виставлено рахунок на {amount} грн.',
            )
            result.append({'invoice_id': inv.id, 'installment': i + 1})

    return Response({'success': True, 'created': result}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_remind(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden

    invoice = Invoice.objects.select_related('student').filter(id=pk).first()
    if not invoice:
        return Response({'success': False, 'error': 'Рахунок не знайдено'}, status=404)

    student = invoice.student
    due_label = invoice.due_date.isoformat() if getattr(invoice, 'due_date', None) else ''
    Notification.objects.create(
        user=student,
        type='invoice',
        title='Нагадування про оплату',
        message=f'Нагадування: рахунок на {float(invoice.amount)} грн до {due_label}.',
    )

    return Response(
        {'success': True, 'message': f'Нагадування надіслано: {student.email}'},
        status=200,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_pay(request, pk):
    from decimal import Decimal, InvalidOperation

    role = _effective_role(getattr(request, 'user', None))
    invoice = Invoice.objects.select_related('student').filter(id=pk).first()
    if not invoice:
        return Response({'success': False, 'error': 'Рахунок не знайдено'}, status=404)

    if role == 'student' and invoice.student_id != request.user.id:
        return Response({'detail': 'Forbidden'}, status=403)
    if role not in ('student', 'admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)

    try:
        amount = Decimal(str(request.data.get('amount')))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'success': False, 'error': 'Некоректна сума'}, status=400)

    if amount <= 0:
        return Response({'success': False, 'error': 'Сума має бути більшою за 0'}, status=400)

    remaining = (invoice.amount or Decimal('0')) - (invoice.paid_amount or Decimal('0'))
    if remaining <= 0:
        return Response({'success': False, 'error': 'Рахунок вже сплачено'}, status=400)
    if amount > remaining:
        return Response({'success': False, 'error': 'Сума більша за залишок до сплати'}, status=400)

    invoice.paid_amount = (invoice.paid_amount or Decimal('0')) + amount
    if invoice.paid_amount >= invoice.amount:
        invoice.paid_amount = invoice.amount
        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
    else:
        invoice.status = 'partial'
    invoice.save(update_fields=['paid_amount', 'status', 'paid_at'])

    Notification.objects.create(
        user=invoice.student,
        type='invoice',
        title='Оплату зафіксовано',
        message=f'Зараховано оплату {float(amount)} грн. Статус: {invoice.status}.',
    )

    return Response({'success': True}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def invoice_submit_receipt(request, pk):
    from decimal import Decimal, InvalidOperation

    role = _effective_role(getattr(request, 'user', None))
    invoice = Invoice.objects.select_related('student').filter(id=pk).first()
    if not invoice:
        return Response({'success': False, 'error': 'Рахунок не знайдено'}, status=404)

    if role != 'student' or invoice.student_id != request.user.id:
        return Response({'detail': 'Forbidden'}, status=403)

    receipt_file = request.FILES.get('receipt')
    if not receipt_file:
        return Response({'success': False, 'error': 'Додайте квитанцію'}, status=400)

    try:
        amount = Decimal(str(request.data.get('amount')))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'success': False, 'error': 'Некоректна сума'}, status=400)
    if amount <= 0:
        return Response({'success': False, 'error': 'Сума має бути більшою за 0'}, status=400)

    remaining = (invoice.amount or Decimal('0')) - (invoice.paid_amount or Decimal('0'))
    if remaining <= 0:
        return Response({'success': False, 'error': 'Рахунок вже сплачено'}, status=400)
    if amount > remaining:
        return Response({'success': False, 'error': 'Сума більша за залишок до сплати'}, status=400)

    safe_name = get_valid_filename(receipt_file.name)
    path = default_storage.save(f'invoice_receipts/{invoice.id}/{safe_name}', receipt_file)
    url = default_storage.url(path)

    note = (request.data.get('note') or '').strip() or None
    rec = InvoicePaymentReceipt.objects.create(
        invoice=invoice,
        student=request.user,
        amount=amount,
        receipt_url=url,
        receipt_name=safe_name,
        status='pending',
        note=note,
    )

    Notification.objects.create(
        user=request.user,
        type='invoice',
        title='Квитанцію надіслано',
        message='Квитанція надіслана на перевірку.',
    )

    return Response({'success': True, 'receipt': {'id': rec.id}}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_receipt_review(request, pk, receipt_id):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden

    invoice = Invoice.objects.select_related('student').filter(id=pk).first()
    if not invoice:
        return Response({'success': False, 'error': 'Рахунок не знайдено'}, status=404)

    receipt = InvoicePaymentReceipt.objects.select_related('student').filter(id=receipt_id, invoice_id=pk).first()
    if not receipt:
        return Response({'success': False, 'error': 'Квитанцію не знайдено'}, status=404)

    action = str(request.data.get('action') or '').strip().lower()
    if action not in ('approve', 'reject'):
        return Response({'success': False, 'error': 'Некоректна дія'}, status=400)

    receipt.reviewed_by = request.user
    receipt.reviewed_at = timezone.now()

    if action == 'reject':
        note = (request.data.get('note') or '').strip() or None
        receipt.status = 'rejected'
        receipt.note = note
        receipt.save(update_fields=['status', 'note', 'reviewed_by', 'reviewed_at'])
        Notification.objects.create(
            user=invoice.student,
            type='invoice',
            title='Квитанцію відхилено',
            message=note or 'Квитанцію відхилено адміністратором.',
        )
        return Response({'success': True}, status=200)

    # approve
    receipt.status = 'approved'
    receipt.note = None
    receipt.save(update_fields=['status', 'note', 'reviewed_by', 'reviewed_at'])

    remaining = (invoice.amount or 0) - (invoice.paid_amount or 0)
    to_apply = receipt.amount
    if to_apply > remaining:
        to_apply = remaining
    if to_apply and to_apply > 0:
        invoice.paid_amount = (invoice.paid_amount or 0) + to_apply
    if invoice.paid_amount >= invoice.amount:
        invoice.paid_amount = invoice.amount
        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
    else:
        invoice.status = 'partial'
    invoice.save(update_fields=['paid_amount', 'status', 'paid_at'])

    Notification.objects.create(
        user=invoice.student,
        type='invoice',
        title='Оплату підтверджено',
        message=f'Квитанцію підтверджено. Зараховано {float(to_apply)} грн.',
    )
    return Response({'success': True}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices_list(request):
    role = _effective_role(getattr(request, 'user', None))
    invoices = Invoice.objects.select_related('student').order_by('-created_at').all()
    if role == 'student':
        invoices = invoices.filter(student=request.user)
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
@permission_classes([IsAuthenticated])
def administrators_list(request):
    forbidden = _require_roles(request, ('superadmin',))
    if forbidden:
        return forbidden
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
    # Public self-registration is disabled.
    # Students must be created by admins (or via approved SSO flows).
    return Response({'detail': 'Not Found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_logout(request):
    response = Response({'success': True}, status=200)
    response.delete_cookie('auth-token')
    return response


def _parse_due_datetime(due_date_raw):
    """Parse due_date from API.

    Frontend often sends YYYY-MM-DD. If we store it as midnight in local TZ,
    serializing to UTC becomes previous day (e.g. 22:00Z). To avoid this,
    we store date-only values as local noon.
    """

    raw = str(due_date_raw or '').strip()
    if not raw:
        return None

    # date-only
    d = parse_date(raw)
    if d and len(raw) == 10:
        try:
            local_tz = timezone.get_current_timezone()
            naive = datetime.datetime(d.year, d.month, d.day, 12, 0, 0)
            return timezone.make_aware(naive, local_tz)
        except Exception:
            return datetime.datetime(d.year, d.month, d.day, 12, 0, 0)

    # full datetime
    dt = parse_datetime(raw)
    if not dt:
        try:
            dt = datetime.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except Exception:
            return None

    if timezone.is_naive(dt):
        try:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        except Exception:
            pass
    return dt


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_me(request):
    user = getattr(request, 'user', None)
    if not isinstance(user, User):
        return Response({'success': True, 'user': None}, status=200)

    effective_role = _effective_role(user) or 'student'
    effective_group_id = getattr(user, 'group_id', None)
    if not effective_group_id:
        try:
            effective_group_id = (
                GroupStudent.objects
                .filter(student_id=user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        except Exception:
            effective_group_id = None

    return Response(
        {
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': effective_role,
                'is_active': user.is_active,
                'is_superadmin': user.is_superadmin,
                'group_id': effective_group_id,
            },
        },
        status=200,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_toggle_status(request, pk):
    forbidden = _require_roles(request, ('superadmin',))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
def admin_delete(request, pk):
    forbidden = _require_roles(request, ('superadmin',))
    if forbidden:
        return forbidden
    try:
        user = User.objects.get(pk=pk)
        if user.is_superadmin:
            return Response({"error": "Неможливо видалити супер-адміна."}, status=403)

        reassign_to = (
            request.data.get('reassign_to_admin_id')
            if hasattr(request, 'data') else None
        ) or request.query_params.get('reassign_to_admin_id')
        target_admin = _parse_admin_target(reassign_to)
        if reassign_to not in (None, '', 'null') and not target_admin:
            return Response({'error': 'Цільового адміністратора не знайдено'}, status=400)
        if target_admin and target_admin.id == user.id:
            return Response({'error': 'Неможливо призначити завдання тому ж адміну'}, status=400)

        _redistribute_admin_tasks(user, target_admin)
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

    password_ok = False
    try:
        password_ok = check_password(password, user.password)
    except Exception:
        password_ok = False

    # Backward compatibility: some users (e.g. seeded superadmin) may have bcrypt hashes.
    # If bcrypt matches, rehash into Django format for future logins.
    if not password_ok:
        try:
            stored = str(user.password or '')
            if stored.startswith(('$2a$', '$2b$', '$2y$')):
                password_ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
                if password_ok:
                    user.password = make_password(password)
                    user.save(update_fields=['password'])
        except Exception:
            password_ok = False

    if not password_ok:
        return Response({'success': False, 'error': 'Невірний email або пароль'}, status=401)
    token = jwt.encode(
        {
            'userId': user.id,
            'exp': timezone.now() + timedelta(days=7),
        },
        settings.JWT_SECRET,
        algorithm='HS256',
    )

    effective_role = user.role
    if getattr(user, 'is_superadmin', False) and effective_role != 'superadmin':
        effective_role = 'superadmin'

    response = Response(
        {
            'success': True,
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': effective_role,
                'is_active': user.is_active,
                'is_superadmin': user.is_superadmin,
                'group_id': user.group_id,
            },
        },
        status=200,
    )

    response.set_cookie(
        'auth-token',
        token,
        httponly=True,
        samesite=os.getenv('AUTH_COOKIE_SAMESITE', 'Lax'),
        secure=os.getenv('AUTH_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes'),
        max_age=60 * 60 * 24 * 7,
        path='/',
    )

    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_google(request):
    """Authenticate with Google ID token.

    Expects JSON: {"id_token": "..."}
    Returns: {success, token, user}
    """
    id_token = request.data.get('id_token')
    if not id_token:
        return Response({'success': False, 'error': 'missing_id_token'}, status=400)

    try:
        with urlopen(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={quote(str(id_token))}"
        ) as response:
            token_info = json.loads(response.read().decode('utf-8'))
    except HTTPError:
        return Response({'success': False, 'error': 'invalid_id_token'}, status=401)
    except URLError:
        return Response({'success': False, 'error': 'google_unreachable'}, status=502)
    except Exception:
        return Response({'success': False, 'error': 'google_auth_failed'}, status=401)

    email = (token_info.get('email') or '').strip().lower()
    if not email:
        return Response({'success': False, 'error': 'google_missing_email'}, status=400)

    expected_aud = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    aud = (token_info.get('aud') or '').strip()
    if expected_aud and aud and aud != expected_aud:
        return Response({'success': False, 'error': 'invalid_audience'}, status=401)

    email_verified = token_info.get('email_verified')
    if str(email_verified).lower() not in ('true', '1', 'yes'):
        return Response({'success': False, 'error': 'email_not_verified'}, status=401)

    user = User.objects.filter(email=email).first()
    if not user:
        # Create a student account by default
        user = User.objects.create(
            email=email,
            name=(token_info.get('name') or email.split('@')[0])[:255],
            password=make_password(os.urandom(24).hex()),
            role='student',
            status='active',
            is_active=True,
            is_superadmin=False,
        )

    effective_role = user.role
    if getattr(user, 'is_superadmin', False) and effective_role != 'superadmin':
        effective_role = 'superadmin'

    token = jwt.encode(
        {
            'userId': user.id,
            'exp': timezone.now() + timedelta(days=7),
        },
        settings.JWT_SECRET,
        algorithm='HS256',
    )

    return Response(
        {
            'success': True,
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': effective_role,
                'is_active': user.is_active,
                'is_superadmin': user.is_superadmin,
                'group_id': user.group_id,
            },
        },
        status=200,
    )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def profile_me(request):
    user = request.user

    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'birth_date': user.birth_date.isoformat() if user.birth_date else None,
                    'registration_address': user.registration_address or '',
                    'avatar_url': user.avatar_url or '',
                    'role': user.role,
                    'is_superadmin': bool(getattr(user, 'is_superadmin', False)),
                },
            },
            status=200,
        )

    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    birth_date_raw = request.data.get('birth_date')
    registration_address = request.data.get('registration_address')
    name = request.data.get('name')
    email = request.data.get('email')

    if first_name is not None:
        user.first_name = str(first_name).strip() or None
    if last_name is not None:
        user.last_name = str(last_name).strip() or None
    if registration_address is not None:
        user.registration_address = str(registration_address).strip() or None

    if birth_date_raw is not None:
        parsed = parse_date(str(birth_date_raw))
        user.birth_date = parsed

    if name is not None and str(name).strip():
        user.name = str(name).strip()
    else:
        # If explicit name wasn't sent, derive from first/last when available
        derived = " ".join([part for part in [user.first_name or '', user.last_name or ''] if part]).strip()
        if derived:
            user.name = derived

    if email is not None:
        next_email = str(email).strip().lower()
        if next_email and next_email != user.email:
            if _effective_role(user) != 'superadmin':
                # Student/admin cannot change their email
                pass
            else:
                if User.objects.exclude(id=user.id).filter(email=next_email).exists():
                    return Response({'success': False, 'error': 'Email вже існує.'}, status=400)
                user.email = next_email

    avatar_file = request.FILES.get('avatar')
    remove_avatar = str(request.data.get('remove_avatar', '')).lower() in ('true', '1', 'yes')
    if remove_avatar:
        user.avatar_url = None
    if avatar_file:
        safe_name = get_valid_filename(getattr(avatar_file, 'name', 'avatar'))
        path = default_storage.save(f"avatars/{user.id}/{safe_name}", avatar_file)
        user.avatar_url = f"{settings.MEDIA_URL}{path}"

    user.save()
    return Response({'success': True}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def profile_change_password(request):
    user = request.user

    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not current_password or not new_password:
        return Response({'success': False, 'error': 'Поточний та новий пароль обовʼязкові'}, status=400)

    if not check_password(str(current_password), user.password):
        return Response({'success': False, 'error': 'Невірний поточний пароль'}, status=400)

    if len(str(new_password)) < 6:
        return Response({'success': False, 'error': 'Пароль має бути не менше 6 символів'}, status=400)

    user.password = make_password(str(new_password))
    user.save()
    return Response({'success': True}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_detail(request, pk):
    viewer = request.user
    if getattr(viewer, 'role', None) not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)

    try:
        target = User.objects.select_related('group').get(id=pk)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Користувача не знайдено'}, status=404)

    if getattr(target, 'is_superadmin', False) and getattr(viewer, 'role', None) != 'superadmin':
        return Response({'detail': 'Forbidden'}, status=403)

    return Response(
        {
            'success': True,
            'user': {
                'id': target.id,
                'email': target.email,
                'name': target.name,
                'first_name': target.first_name or '',
                'last_name': target.last_name or '',
                'birth_date': target.birth_date.isoformat() if target.birth_date else None,
                'registration_address': target.registration_address or '',
                'avatar_url': target.avatar_url or '',
                'role': target.role,
                'is_superadmin': bool(getattr(target, 'is_superadmin', False)),
                'group': {
                    'id': target.group.id,
                    'name': target.group.name,
                    'color': target.group.color,
                } if target.group else None,
            },
        },
        status=200,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_recent_activity(request):
    """Return a unified feed of recent activity for the admin dashboard."""
    if getattr(request.user, 'role', None) not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)

    group_id_raw = request.query_params.get('group_id')
    group_id = int(group_id_raw) if group_id_raw and str(group_id_raw).isdigit() else None

    activities: list[dict] = []

    def add_activity(*, type_: str, action: str, name: str, timestamp, group_obj=None):
        if not timestamp:
            return
        group_payload = None
        if group_obj is not None:
            try:
                group_payload = {
                    'id': group_obj.id,
                    'name': group_obj.name,
                    'color': getattr(group_obj, 'color', None),
                }
            except Exception:
                group_payload = None

        try:
            ts = timestamp
            if isinstance(ts, datetime.datetime):
                ts = timezone.localtime(ts).isoformat()
            elif isinstance(ts, datetime.date):
                ts = ts.isoformat()
            else:
                ts = str(ts)
        except Exception:
            ts = ''

        activities.append(
            {
                'type': type_,
                'action': action,
                'name': name,
                'timestamp': ts,
                'group': group_payload,
            }
        )

    groups_qs = Group.objects.all().order_by('-created_at')
    if group_id is not None:
        groups_qs = groups_qs.filter(id=group_id)
    for group in groups_qs[:10]:
        add_activity(
            type_='group',
            action='created',
            name=group.name,
            timestamp=group.created_at,
            group_obj=group,
        )

    lessons_qs = Lesson.objects.select_related('group').order_by('-created_at')
    if group_id is not None:
        lessons_qs = lessons_qs.filter(group_id=group_id)
    for lesson in lessons_qs[:10]:
        add_activity(
            type_='lesson',
            action='created',
            name=lesson.title,
            timestamp=lesson.created_at,
            group_obj=lesson.group,
        )

    tasks_qs = Task.objects.select_related('group').order_by('-created_at')
    if group_id is not None:
        tasks_qs = tasks_qs.filter(group_id=group_id)
    for task in tasks_qs[:10]:
        add_activity(
            type_='task',
            action='created',
            name=task.title,
            timestamp=task.created_at,
            group_obj=task.group,
        )

    if group_id is None:
        for news in News.objects.order_by('-created_at')[:10]:
            add_activity(
                type_='news',
                action='created',
                name=news.title,
                timestamp=news.created_at,
                group_obj=None,
            )

    activities.sort(key=lambda a: a.get('timestamp', ''), reverse=True)
    return Response(activities[:50])


# ===== STUDENTS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def students_list(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    if request.method == 'POST':
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        phone = (request.data.get('phone') or '').strip()
        group_id = request.data.get('group_id', None)

        if not (name and email and password):
            return Response({'error': 'Всі поля обовʼязкові!'}, status=400)
        if len(password) < 6:
            return Response({'error': 'Пароль має бути не менше 6 символів!'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email вже існує.'}, status=400)

        group = None
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return Response({'error': 'Група не знайдена.'}, status=404)

        user = User.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            is_active=True,
            is_superadmin=False,
            role='student',
            phone=phone or None,
            group=group,
        )

        if group:
            GroupStudent.objects.get_or_create(group=group, student=user)

        return Response({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active
        }, status=201)

    # --- Ось тут має бути визначення students!
    students = User.objects.select_related('group').filter(
        models.Q(role__iexact='student') | models.Q(role__iexact='user')
    )

    # Map studentId -> group (fallback for legacy data where Users.group is null).
    memberships = (
        GroupStudent.objects
        .select_related('group')
        .filter(student_id__in=students.values_list('id', flat=True))
    )
    group_by_student_id: dict[int, Group] = {}
    for m in memberships:
        # If multiple groups exist (unexpected), keep the first.
        group_by_student_id.setdefault(int(m.student_id), m.group)

    payload = []
    for u in students:
        g = getattr(u, 'group', None) or group_by_student_id.get(int(u.id))
        payload.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_active": u.is_active,
            "group": {
                "id": g.id,
                "name": g.name,
                "color": g.color,
            } if g else None,
        })
    return Response(payload)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def student_detail(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    try:
        student = User.objects.get(id=pk)
        if _effective_role(student) != 'student':
            raise User.DoesNotExist
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
        group_id = request.data.get('group_id', None)
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

        # Optional group update (keeps legacy GroupStudent table in sync)
        if group_id is not None:
            group = None
            if str(group_id).strip() not in ('', 'null', 'None'):
                try:
                    group = Group.objects.get(id=group_id)
                except Group.DoesNotExist:
                    return Response({'success': False, 'error': 'Група не знайдена.'}, status=404)

            if group is None:
                GroupStudent.objects.filter(student=student).delete()
                if getattr(student, 'group_id', None) is not None:
                    student.group = None
                    student.save(update_fields=['group'])
            else:
                # ensure membership exists
                GroupStudent.objects.get_or_create(group=group, student=student)
                # optional: clear other memberships to avoid ambiguity
                GroupStudent.objects.filter(student=student).exclude(group=group).delete()
                if getattr(student, 'group_id', None) != group.id:
                    student.group = group
                    student.save(update_fields=['group'])

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
@permission_classes([IsAuthenticated])
def group_add_students(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
            student = User.objects.get(id=student_id)
            if _effective_role(student) != 'student':
                continue
            created = False
            if not GroupStudent.objects.filter(group=group, student=student).exists():
                GroupStudent.objects.create(group=group, student=student)
                created = True

            # Keep denormalized FK in sync even when membership already existed.
            if getattr(student, 'group_id', None) != group.id:
                student.group = group
                student.save(update_fields=['group'])

            if created:
                added_count += 1
        except User.DoesNotExist:
            continue

    return Response({
        'success': True,
        'message': f'Додано {added_count} студентів'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def group_remove_student(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    """Видалити студента з групи"""
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)

    student_id = request.data.get('student_id')

    if not student_id:
        return Response({'success': False, 'error': 'Не вказано студента'}, status=400)

    try:
        student = User.objects.get(id=student_id)
        if _effective_role(student) != 'student':
            return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)
        GroupStudent.objects.filter(group=group, student=student).delete()
        if getattr(student, 'group_id', None) == group.id:
            student.group = None
            student.save(update_fields=['group'])
        return Response({'success': True, 'message': 'Студента видалено з групи'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Студент не знайдений'}, status=404)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def groups_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
                'created_at': group.created_at.isoformat() if group.created_at else '',
                'students': []
            }
        }, status=201)

    groups = Group.objects.all()
    if role == 'student':
        group_ids = []
        try:
            if getattr(request.user, 'group_id', None):
                group_ids.append(int(request.user.group_id))
        except Exception:
            pass
        try:
            extra = list(
                GroupStudent.objects.filter(student_id=request.user.id).values_list('group_id', flat=True)
            )
            group_ids.extend([int(x) for x in extra if x is not None])
        except Exception:
            pass

        group_ids = list(dict.fromkeys(group_ids))
        if group_ids:
            groups = groups.filter(id__in=group_ids)
        else:
            groups = groups.none()

    result = []
    for group in groups:
        students_data = []
        if role in ('admin', 'superadmin'):
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
            'created_at': group.created_at.isoformat() if group.created_at else '',
            'students': students_data
        })

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def group_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        group = Group.objects.get(id=pk)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': 'Група не знайдена'}, status=404)

    if role == 'student':
        allowed_ids = []
        try:
            if getattr(request.user, 'group_id', None):
                allowed_ids.append(int(request.user.group_id))
        except Exception:
            pass
        try:
            extra = list(
                GroupStudent.objects.filter(student_id=request.user.id).values_list('group_id', flat=True)
            )
            allowed_ids.extend([int(x) for x in extra if x is not None])
        except Exception:
            pass
        allowed_ids = list(dict.fromkeys(allowed_ids))
        if group.id not in allowed_ids:
            return Response({'detail': 'Forbidden'}, status=403)

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
            'created_at': group.created_at.isoformat() if group.created_at else '',
            'students': students_data
        })

    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        group.delete()
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_students(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
def subjects_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
@permission_classes([IsAuthenticated])
def subject_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        subject = Subject.objects.get(id=pk)
    except Subject.DoesNotExist:
        return Response({'success': False, 'error': 'Предмет не знайдений'}, status=404)
    if request.method == 'GET':
        return Response({'id': subject.id, 'name': subject.name, 'short_name': subject.short_name,
                         'description': subject.description, 'color': subject.color})
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        subject.name = request.data.get('name', subject.name)
        subject.short_name = request.data.get('short_name', subject.short_name)
        subject.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        subject.delete()
        return Response({'success': True})


# ===== LESSONS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lessons_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
    if role == 'student':
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if effective_group_id:
            lessons = lessons.filter(group_id=effective_group_id)
        else:
            lessons = lessons.none()
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
            'is_online': True if (lesson.meeting_link or '').strip() else False,
            'location': '',
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
@permission_classes([IsAuthenticated])
def lesson_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        lesson = Lesson.objects.select_related('subject', 'group').get(id=pk)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдено'}, status=404)

    if role == 'student':
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if effective_group_id != getattr(lesson, 'group_id', None):
            return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'GET':
        return Response({
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'date': lesson.date.isoformat(),
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'meeting_link': lesson.meeting_link or '',
            'is_online': True if (lesson.meeting_link or '').strip() else False,
            'location': '',
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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        lesson.delete()
        return Response({'success': True})


@api_view(['GET'])
def lesson_grades(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    try:
        lesson = Lesson.objects.get(id=pk)
        grades = LessonGrade.objects.filter(lesson=lesson)
        return Response(
            [{'id': g.id, 'student': g.student.name, 'grade': g.grade, 'comment': g.comment} for g in grades])
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдений'}, status=404)


# ===== TASKS =====
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def task_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)

    if role == 'student':
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if effective_group_id != getattr(task, 'group_id', None):
            return Response({'detail': 'Forbidden'}, status=403)
    elif role == 'admin' and not _can_admin_manage_task(request.user, task):
        return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'GET':
        return Response({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'due_date': task.due_date.isoformat() if getattr(task, 'due_date', None) else '',
            'status': task.status,
            'assigned_admin_id': task.assigned_admin_id,
            'created_at': task.created_at.isoformat() if getattr(task, 'created_at', None) else ''
        })

    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        task.delete()
        return Response({'success': True})

    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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

        if 'assigned_admin_id' in request.data:
            if role != 'superadmin':
                return Response({'detail': 'Forbidden'}, status=403)

            raw_assigned_admin_id = request.data.get('assigned_admin_id')
            if raw_assigned_admin_id in (None, '', 'null'):
                task.assigned_admin = None
            else:
                try:
                    assigned_admin_id = int(raw_assigned_admin_id)
                except (TypeError, ValueError):
                    return Response({'success': False, 'error': 'Некоректний assigned_admin_id'}, status=400)

                assigned_admin = User.objects.filter(id=assigned_admin_id, role='admin').first()
                if not assigned_admin:
                    return Response({'success': False, 'error': 'Адміністратора не знайдено'}, status=404)
                task.assigned_admin = assigned_admin

        task.save()
        return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def tasks_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        # POST код залишається без змін
        title = request.data.get('title', '')
        if not title:
            return Response({'success': False, 'error': 'Назва завдання обов\'язкова'}, status=400)

        due_date = _parse_due_datetime(request.data.get('due_date'))

        # Валідація дати
        if due_date:
            try:
                today = timezone.localdate()
                due_d = timezone.localtime(due_date).date() if isinstance(due_date, datetime.datetime) else None
                if due_d and due_d < today:
                    return Response({'success': False, 'error': 'Не можна вказувати дату раніше поточного дня'}, status=400)
            except Exception:
                pass

        # Отримуємо group і subject
        group = None
        subject = None

        group_id = request.data.get('group_id')
        if not group_id:
            return Response({'success': False, 'error': 'Оберіть групу'}, status=400)
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'success': False, 'error': 'Групу не знайдено'}, status=404)

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
            subject=subject,
            assigned_admin=request.user if role == 'admin' else None,
        )

        return Response({
            'success': True,
            'task': {
                'id': task.id,
                'title': task.title,
                'type': task.type,
                'max_grade': task.max_grade,
                'due_date': task.due_date.isoformat() if getattr(task, 'due_date', None) else '',
                'assigned_admin_id': task.assigned_admin_id,
                'group': {'id': group.id, 'name': group.name, 'color': group.color} if group else None,
                'subject': {'id': subject.id, 'name': subject.name, 'short_name': subject.short_name,
                            'color': subject.color} if subject else None,
            }
        }, status=201)

    # GET - повертаємо всі завдання з повною інформацією
    tasks = Task.objects.select_related('subject', 'group', 'assigned_admin').all()
    if role == 'student':
        group_ids = []
        try:
            if getattr(request.user, 'group_id', None):
                group_ids.append(int(request.user.group_id))
        except Exception:
            pass

        try:
            extra_ids = list(
                GroupStudent.objects.filter(student_id=request.user.id).values_list('group_id', flat=True)
            )
            group_ids.extend([int(x) for x in extra_ids if x is not None])
        except Exception:
            pass

        group_ids = list(dict.fromkeys(group_ids))

        if group_ids:
            tasks = tasks.filter(group_id__in=group_ids)
        else:
            tasks = tasks.none()
    elif role in ('admin', 'superadmin'):
        tasks = _scope_tasks_for_role(request.user, tasks)
    else:
        return Response({'detail': 'Forbidden'}, status=403)
    result = []

    submission_by_task_id = {}
    if role == 'student':
        try:
            task_ids = list(tasks.values_list('id', flat=True))
            subs = (
                TaskSubmission.objects
                .filter(student=request.user, task_id__in=task_ids)
                .prefetch_related('files')
                .only('id', 'task_id', 'status', 'grade', 'teacher_comment', 'comment', 'submitted_at')
            )
            for s in subs:
                submission_by_task_id[int(s.task_id)] = s
        except Exception:
            submission_by_task_id = {}

    for task in tasks:
        submission = submission_by_task_id.get(int(task.id)) if role == 'student' else None
        task_data = {
            'id': task.id,
            'title': task.title,
            'type': task.type,
            'description': task.description,
            'due_date': task.due_date.isoformat() if getattr(task, 'due_date', None) else '',
            'max_grade': task.max_grade,
            'created_at': task.created_at.isoformat() if getattr(task, 'created_at', None) else '',
            'subject': None,
            'group': None,
            'assigned_admin_id': task.assigned_admin_id,
            'submission': (
                {
                    'id': submission.id,
                    'status': submission.status,
                    'grade': submission.grade,
                    'comment': submission.comment,
                    'teacher_comment': getattr(submission, 'teacher_comment', None),
                    'submitted_at': submission.submitted_at.isoformat() if getattr(submission, 'submitted_at', None) else None,
                    'files': [
                        {
                            'id': f.id,
                            'name': f.file_name,
                            'url': _absolute_file_url(request, getattr(f, 'file_url', '')),
                            'size': f.file_size,
                            'type': f.file_type,
                        }
                        for f in submission.files.all()
                    ] if hasattr(submission, 'files') else [],
                }
                if submission is not None
                else None
            ) if role == 'student' else None,
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
@permission_classes([IsAuthenticated])
def tasks_bulk_create(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    """Масове створення завдань для кількох груп"""
    title = request.data.get('title', '')
    description = request.data.get('description', '')
    task_type = request.data.get('type', 'homework')
    due_date = _parse_due_datetime(request.data.get('due_date'))
    max_grade = request.data.get('max_grade', 100)
    group_ids = request.data.get('group_ids', [])
    subject_id = request.data.get('subject_id')

    if not title:
        return Response({'success': False, 'error': 'Назва завдання обов\'язкова'}, status=400)

    if not group_ids or len(group_ids) == 0:
        return Response({'success': False, 'error': 'Оберіть хоча б одну групу'}, status=400)

    # Валідація дати
    if due_date:
        try:
            today = timezone.localdate()
            due_d = timezone.localtime(due_date).date() if isinstance(due_date, datetime.datetime) else None
            if due_d and due_d < today:
                return Response({'success': False, 'error': 'Не можна вказувати дату раніше поточного дня'}, status=400)
        except Exception:
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
                subject=subject,
                assigned_admin=request.user if _effective_role(request.user) == 'admin' else None,
            )
            created_tasks.append({
                'id': task.id,
                'title': task.title,
                'group': group.name,
                'assigned_admin_id': task.assigned_admin_id,
            })
        except Group.DoesNotExist:
            continue

    return Response({
        'success': True,
        'message': f'Створено {len(created_tasks)} завдань',
        'tasks': created_tasks
    }, status=201)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def task_submissions(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        task = Task.objects.select_related('group').get(id=pk)
    except Task.DoesNotExist:
        return Response({'success': False, 'error': 'Завдання не знайдено'}, status=404)

    if role == 'student':
        group_ids = []
        try:
            if getattr(request.user, 'group_id', None):
                group_ids.append(int(request.user.group_id))
        except Exception:
            pass

        try:
            extra_ids = list(
                GroupStudent.objects.filter(student_id=request.user.id).values_list('group_id', flat=True)
            )
            group_ids.extend([int(x) for x in extra_ids if x is not None])
        except Exception:
            pass

        group_ids = list(dict.fromkeys(group_ids))
        if not group_ids or int(getattr(task, 'group_id', 0) or 0) not in group_ids:
            return Response({'detail': 'Forbidden'}, status=403)
    elif role == 'admin' and not _can_admin_manage_task(request.user, task):
        return Response({'detail': 'Forbidden'}, status=403)
    elif role not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'POST':
        if role != 'student':
            return Response({'detail': 'Forbidden'}, status=403)

        comment = str(request.data.get('comment', '') or '').strip() or None
        files = []
        try:
            files = request.FILES.getlist('files')
        except Exception:
            files = []

        if not comment and not files:
            return Response({'success': False, 'error': 'Додайте файл або коментар'}, status=400)

        submission, _created = TaskSubmission.objects.get_or_create(
            task=task,
            student=request.user,
            defaults={'status': 'submitted', 'comment': comment, 'submitted_at': timezone.now()},
        )

        if submission.status == 'graded':
            return Response({'success': False, 'error': 'Це завдання вже оцінене і не може бути перездане'}, status=400)

        submission.comment = comment
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save(update_fields=['comment', 'status', 'submitted_at'])

        saved_files = []
        for f in files:
            safe_name = get_valid_filename(getattr(f, 'name', 'file'))
            stored_path = default_storage.save(f"submissions/{task.id}/{submission.id}/{safe_name}", f)
            url = f"{settings.MEDIA_URL}{stored_path}"
            file_rec = SubmissionFile.objects.create(
                submission=submission,
                file_name=safe_name,
                file_url=url,
                file_size=str(getattr(f, 'size', '') or ''),
                file_type=str(getattr(f, 'content_type', '') or 'file')[:20],
            )
            saved_files.append({'id': file_rec.id, 'name': file_rec.file_name, 'url': file_rec.file_url, 'size': file_rec.file_size})

        for item in saved_files:
            item['url'] = _absolute_file_url(request, item.get('url'))

        if getattr(task, 'assigned_admin_id', None):
            try:
                Notification.objects.create(
                    user_id=task.assigned_admin_id,
                    type='task_submission',
                    title='Нова здача ДЗ',
                    message=f"{request.user.name} здав(ла) завдання: {task.title}",
                    link='/admin/homework',
                )
            except Exception:
                pass

        return Response({'success': True, 'submission': {'id': submission.id, 'status': submission.status, 'files': saved_files}}, status=201)

    submissions_qs = (
        TaskSubmission.objects
        .select_related('student')
        .prefetch_related('files')
        .filter(task=task)
    )
    if role == 'student':
        submissions_qs = submissions_qs.filter(student=request.user)
        return Response([
            {
                'id': s.id,
                'status': s.status,
                'grade': s.grade,
                'comment': s.comment,
                'teacher_comment': getattr(s, 'teacher_comment', None) or None,
                'submitted_at': s.submitted_at.isoformat() if getattr(s, 'submitted_at', None) else None,
                'files': [
                    {'id': f.id, 'name': f.file_name, 'url': _absolute_file_url(request, f.file_url), 'size': f.file_size, 'type': f.file_type}
                    for f in s.files.all()
                ],
            }
            for s in submissions_qs
        ])

    if role not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)
    return Response(
        [
            {
                'id': s.id,
                'student': s.student.name,
                'student_id': s.student_id,
                'status': s.status,
                'grade': s.grade,
                'comment': s.comment,
                'teacher_comment': getattr(s, 'teacher_comment', None) or None,
                'submitted_at': s.submitted_at.isoformat() if getattr(s, 'submitted_at', None) else None,
                'files': [
                    {
                        'id': f.id,
                        'name': f.file_name,
                        'url': _absolute_file_url(request, f.file_url),
                        'size': f.file_size,
                        'type': f.file_type,
                    }
                    for f in s.files.all()
                ],
            }
            for s in submissions_qs
        ]
    )


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def grade_submission(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden

    try:
        submission = TaskSubmission.objects.select_related('task', 'student').get(id=pk)
    except TaskSubmission.DoesNotExist:
        return Response({'success': False, 'error': 'Здачу не знайдено'}, status=404)

    if _effective_role(request.user) == 'admin' and not _can_admin_manage_task(request.user, submission.task):
        return Response({'detail': 'Forbidden'}, status=403)

    requested_status = request.data.get('status', None)
    requested_action = request.data.get('action', None)
    if isinstance(requested_status, str):
        requested_status = requested_status.strip().lower()
    if isinstance(requested_action, str):
        requested_action = requested_action.strip().lower()

    # Support "return/reject" flow (no grade required)
    if requested_status == 'returned' or requested_action in ('return', 'reject', 'returned'):
        teacher_comment = request.data.get('teacher_comment', None)
        if teacher_comment is None:
            teacher_comment = request.data.get('comment', None)

        submission.grade = None
        submission.teacher_comment = (str(teacher_comment).strip() if teacher_comment is not None else None) or None
        submission.status = 'returned'
        submission.graded_at = timezone.now()
        submission.save(update_fields=['grade', 'teacher_comment', 'status', 'graded_at'])

        # If the submission is returned, remove previously awarded points for this task.
        try:
            StudentPoint.objects.filter(
                student=submission.student,
                source_type='task',
                source_id=submission.task_id,
            ).delete()
        except Exception:
            pass

        try:
            Notification.objects.create(
                user=submission.student,
                type='task',
                title='Повернено на доопрацювання',
                message=(f"{submission.task.title}: повернено" + (f". {submission.teacher_comment}" if submission.teacher_comment else '')),
                link='/dashboard/learning',
            )
        except Exception:
            pass

        return Response({
            'success': True,
            'submission': {
                'id': submission.id,
                'task_id': submission.task_id,
                'student_id': submission.student_id,
                'status': submission.status,
                'grade': submission.grade,
                'teacher_comment': submission.teacher_comment,
                'graded_at': submission.graded_at.isoformat() if submission.graded_at else None,
            }
        })

    raw_grade = request.data.get('grade', None)
    if raw_grade is None:
        raw_grade = request.data.get('score', None)

    if raw_grade is None or str(raw_grade).strip() == '':
        return Response({'success': False, 'error': 'Вкажіть оцінку'}, status=400)

    try:
        grade_value = int(raw_grade)
    except (TypeError, ValueError):
        return Response({'success': False, 'error': 'Оцінка має бути числом'}, status=400)

    max_grade = int(getattr(submission.task, 'max_grade', 100) or 100)
    if grade_value < 0 or grade_value > max_grade:
        return Response({'success': False, 'error': f'Оцінка має бути в межах 0-{max_grade}'}, status=400)

    teacher_comment = request.data.get('teacher_comment', None)
    if teacher_comment is None:
        teacher_comment = request.data.get('comment', None)

    submission.grade = grade_value
    submission.teacher_comment = (str(teacher_comment).strip() if teacher_comment is not None else None) or None
    submission.status = 'graded'
    submission.graded_at = timezone.now()
    submission.save(update_fields=['grade', 'teacher_comment', 'status', 'graded_at'])

    # Award/update points for the task grade so leaderboard & balance reflect homework results.
    try:
        desc = f"Оцінка за завдання: {submission.task.title}" if getattr(submission, 'task', None) else "Оцінка за завдання"
        existing = (
            StudentPoint.objects
            .filter(student=submission.student, source_type='task', source_id=submission.task_id)
            .order_by('id')
        )
        first = existing.first()
        if first:
            existing.exclude(id=first.id).delete()
            first.points = int(grade_value)
            first.description = desc
            first.save(update_fields=['points', 'description'])
        else:
            StudentPoint.objects.create(
                student=submission.student,
                points=int(grade_value),
                source_type='task',
                source_id=submission.task_id,
                description=desc,
            )
    except Exception:
        pass

    try:
        Notification.objects.create(
            user=submission.student,
            type='grade',
            title='Оцінка за завдання',
            message=f"{submission.task.title}: {grade_value}/{max_grade}" + (
                f". {submission.teacher_comment}" if submission.teacher_comment else ''
            ),
            link='/dashboard/learning',
        )
    except Exception:
        pass

    return Response({
        'success': True,
        'submission': {
            'id': submission.id,
            'task_id': submission.task_id,
            'student_id': submission.student_id,
            'status': submission.status,
            'grade': submission.grade,
            'teacher_comment': submission.teacher_comment,
            'graded_at': submission.graded_at.isoformat() if submission.graded_at else None,
        }
    })


# ===== GRADES & ATTENDANCE =====

@api_view(['GET'])
def grades_list(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    grades = LessonGrade.objects.all()
    return Response(
        [{'id': g.id, 'student': g.student.name, 'lesson': g.lesson.title, 'grade': g.grade} for g in grades])


# ===== ATTENDANCE =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def attendance_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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

    # GET - повертаємо записи (опційно фільтруємо)
    attendance_records = Attendance.objects.select_related('lesson', 'user', 'lesson__group', 'lesson__subject').all()
    lesson_id = request.query_params.get('lesson_id')
    if lesson_id is not None and str(lesson_id).strip():
        attendance_records = attendance_records.filter(lesson_id=lesson_id)
    if role == 'student':
        attendance_records = attendance_records.filter(user=request.user)
    elif role not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)
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
@permission_classes([IsAuthenticated])
def attendance_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        attendance = Attendance.objects.select_related('lesson', 'user').get(id=pk)
    except Attendance.DoesNotExist:
        return Response({'success': False, 'error': 'Запис не знайдено'}, status=404)

    if role == 'student' and attendance.user_id != request.user.id:
        return Response({'detail': 'Forbidden'}, status=403)
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'GET':
        return Response({
            'id': attendance.id,
            'status': attendance.status,
            'notes': attendance.notes or '',
            'lesson_id': attendance.lesson.id,
            'user_id': attendance.user.id,
        })

    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        attendance.status = request.data.get('status', attendance.status)
        attendance.notes = request.data.get('notes', attendance.notes)
        attendance.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        attendance.delete()
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_by_lesson(request, lesson_id=None):
    """
    GET /api/attendance/?lesson_id=XXX
    Повернути {lesson, students: [user, attendance]}
    """
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden

    lesson_id = lesson_id or request.query_params.get('lesson_id')
    if not lesson_id:
        return Response({'success': False, 'error': 'Потрібен lesson_id'}, status=400)

    try:
        lesson = Lesson.objects.select_related('group').get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response({'success': False, 'error': 'Урок не знайдено'}, status=404)

    students = User.objects.filter(group=lesson.group, role='student')
    if lesson.group_id:
        legacy_student_ids = (
            GroupStudent.objects.filter(group_id=lesson.group_id)
            .values_list('student_id', flat=True)
        )
        students = User.objects.filter(
            models.Q(id__in=legacy_student_ids) | models.Q(group=lesson.group),
            role='student',
        ).distinct()
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
            'date': lesson.date.isoformat() if lesson.date else '',
            'group': {
                'id': lesson.group.id,
                'name': lesson.group.name,
                'color': lesson.group.color,
            }
        },
        'students': result,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_my(request):
    role = _effective_role(getattr(request, 'user', None))
    if role != 'student':
        return Response({'detail': 'Forbidden'}, status=403)

    month = str(request.query_params.get('month', '') or '').strip()  # YYYY-MM
    if month and len(month) != 7:
        month = ''

    qs = Attendance.objects.select_related('lesson').filter(user=request.user)
    if month:
        qs = qs.filter(lesson__date__startswith=month)

    return Response([
        {
            'id': a.id,
            'status': a.status,
            'notes': a.notes or '',
            'lesson': {
                'id': a.lesson_id,
                'title': a.lesson.title,
                'date': a.lesson.date.isoformat() if a.lesson.date else '',
            },
        }
        for a in qs.order_by('-lesson__date')
    ])

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

        # Sync student's group with the lesson's group for consistency.
        try:
            lesson = Lesson.objects.select_related('group').get(id=lesson_id)
            if lesson.group_id:
                student = User.objects.filter(id=user_id, role='student').first()
                if student:
                    GroupStudent.objects.get_or_create(group_id=lesson.group_id, student_id=student.id)
                    if getattr(student, 'group_id', None) != lesson.group_id:
                        student.group_id = lesson.group_id
                        student.save(update_fields=['group'])
        except Exception:
            pass

        if is_new:
            created += 1
        else:
            updated += 1

    return Response({'success': True, 'created': created, 'updated': updated})

# ===== INVOICES =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invoices_list(request):
    role = _effective_role(getattr(request, 'user', None))

    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        return create_invoice(request)

    invoices_qs = (
        Invoice.objects
        .select_related('student')
        .prefetch_related('receipts')
        .order_by('-created_at')
        .all()
    )
    if role == 'student':
        invoices_qs = invoices_qs.filter(student=request.user)
    elif role not in ('admin', 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)

    data = []
    for i in invoices_qs:
        latest_receipt = None
        try:
            receipts = list(i.receipts.all())
            receipts.sort(key=lambda r: (r.created_at or timezone.now()), reverse=True)
            latest_receipt = receipts[0] if receipts else None
        except Exception:
            latest_receipt = None

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
            'latestReceipt': (
                {
                    'id': latest_receipt.id,
                    'amount': float(latest_receipt.amount),
                    'receiptUrl': latest_receipt.receipt_url,
                    'receiptName': latest_receipt.receipt_name,
                    'status': latest_receipt.status,
                    'note': latest_receipt.note or '',
                    'createdAt': latest_receipt.created_at.isoformat() if latest_receipt.created_at else '',
                }
                if latest_receipt
                else None
            ),
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices_history(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    invoices = Invoice.objects.select_related('student').order_by('-created_at').all()
    return Response([
        {
            'id': i.id,
            'studentId': i.student.id,
            'studentName': i.student.name,
            'studentEmail': i.student.email,
            'amount': float(i.amount),
            'paidAmount': float(i.paid_amount),
            'status': i.status,
            'dueDate': i.due_date.isoformat() if i.due_date else '',
            'createdAt': i.created_at.isoformat() if i.created_at else '',
        }
        for i in invoices
    ])


# ===== ADMIN & STATS =====

@api_view(['GET'])
def admin_stats(request):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    return Response(
        {'students': User.objects.filter(role='student').count(), 'admins': User.objects.filter(role='admin').count(),
         'groups': Group.objects.count()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    forbidden = _require_roles(request, ('admin', 'superadmin', 'student'))
    if forbidden:
        return forbidden

    # Include students with 0 points so the leaderboard isn't empty on fresh DBs.
    students = (
        User.objects
        .filter(models.Q(role__iexact='student') | models.Q(role__iexact='user'))
        .annotate(total=Coalesce(Sum('points__points'), 0))
        .order_by('-total', 'id')[:10]
    )

    payload = []
    for idx, student in enumerate(students, start=1):
        payload.append({
            'id': student.id,
            'name': getattr(student, 'name', None) or f"Учень {idx}",
            'avatar': getattr(student, 'avatar_url', None) or '',
            'points': int(getattr(student, 'total', 0) or 0),
            'rank': idx,
        })

    return Response(payload)


# ===== ACHIEVEMENTS / POINTS =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def points_me(request):
    role = _effective_role(getattr(request, 'user', None))
    if role != 'student':
        return Response({'detail': 'Forbidden'}, status=403)

    total = (
        StudentPoint.objects
        .filter(student=request.user)
        .aggregate(total=Sum('points'))
        .get('total')
        or 0
    )
    return Response({'totalPoints': int(total)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def achievements_me(request):
    role = _effective_role(getattr(request, 'user', None))
    if role != 'student':
        return Response({'detail': 'Forbidden'}, status=403)

    student = request.user

    submissions = (
        TaskSubmission.objects
        .select_related('task')
        .filter(student=student)
    )
    submissions_count = submissions.count()

    present_count = Attendance.objects.filter(user=student, status='present').count()

    excellent_count = LessonGrade.objects.filter(student=student, grade__gte=10).count()

    speedrunner = 0
    timely = 0
    for s in submissions:
        task = getattr(s, 'task', None)
        due = getattr(task, 'due_date', None) if task else None
        submitted_at = getattr(s, 'submitted_at', None)
        if not (due and submitted_at):
            continue
        try:
            if submitted_at <= due:
                timely += 1
            if submitted_at <= (due - datetime.timedelta(days=1)):
                speedrunner += 1
        except Exception:
            pass

    in_team = TeamMember.objects.filter(student=student).exists()

    # марафон: підрахунок поточної серії днів активності (attendance present або submission)
    activity_days = set()
    for a in Attendance.objects.select_related('lesson').filter(user=student, status='present'):
        try:
            if a.lesson and a.lesson.date:
                activity_days.add(a.lesson.date)
        except Exception:
            pass
    for s in submissions:
        try:
            if s.submitted_at:
                activity_days.add(timezone.localtime(s.submitted_at).date())
        except Exception:
            pass

    streak = 0
    if activity_days:
        day = timezone.localdate()
        while day in activity_days and streak < 30:
            streak += 1
            day = day - datetime.timedelta(days=1)

    def _ach(aid: int, title: str, description: str, progress: int, max_progress: int, points: int):
        progress = int(progress or 0)
        max_progress = int(max_progress or 1)
        unlocked = progress >= max_progress
        if progress > max_progress:
            progress = max_progress
        return {
            'id': aid,
            'title': title,
            'description': description,
            'progress': progress,
            'maxProgress': max_progress,
            'points': int(points),
            'isUnlocked': bool(unlocked),
        }

    payload = [
        _ach(1, 'Перші кроки', 'Завершіть перше завдання', 1 if submissions_count > 0 else 0, 1, 20),
        _ach(2, 'Активний учень', 'Відвідайте 5 занять', present_count, 5, 30),
        _ach(3, 'Відмінник', "Отримайте 5 оцінок 'Відмінно'", excellent_count, 5, 40),
        _ach(4, 'Спідранер', 'Здайте завдання за день до дедлайну', speedrunner, 3, 25),
        _ach(5, "Книжковий черв'як", 'Перегляньте всі матеріали курсу', 0, 10, 35),
        _ach(6, 'Точність', 'Здайте 10 завдань вчасно', timely, 10, 50),
        _ach(7, 'Командний гравець', 'Візьміть участь у груповому проекті', 1 if in_team else 0, 1, 20),
        _ach(8, 'Марафонець', 'Навчайтесь 30 днів поспіль', streak, 30, 60),
    ]

    # Persist achievement rewards into StudentPoint so they affect balance/leaderboard.
    # Idempotent: one record per achievement id.
    try:
        unlocked_ids = [int(a.get('id')) for a in payload if a.get('isUnlocked')]
        if unlocked_ids:
            existing = set(
                StudentPoint.objects
                .filter(student=student, source_type='achievement', source_id__in=unlocked_ids)
                .values_list('source_id', flat=True)
            )
            to_create = []
            for a in payload:
                if not a.get('isUnlocked'):
                    continue
                aid = int(a.get('id'))
                if aid in existing:
                    continue
                pts = int(a.get('points') or 0)
                if pts <= 0:
                    continue
                title = str(a.get('title') or 'Achievement')
                to_create.append(
                    StudentPoint(
                        student=student,
                        points=pts,
                        source_type='achievement',
                        source_id=aid,
                        description=f'Досягнення: {title}',
                    )
                )
            if to_create:
                StudentPoint.objects.bulk_create(to_create)
    except Exception:
        pass

    return Response(payload)


# ===== NEWS =====


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def news_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        # --- Валідація та отримання значень ---
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        category = request.data.get('category', '').strip()
        image_url = request.data.get('image_url', '')
        video_url = request.data.get('video_url', '')
        link = request.data.get('link', '')

        image_file = request.FILES.get('image_file')
        if image_file:
            safe_name = get_valid_filename(getattr(image_file, 'name', 'image'))
            stored_path = default_storage.save(f"news_images/{safe_name}", image_file)
            image_url = default_storage.url(stored_path)

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
    news_qs = News.objects.order_by("-created_at")
    if role == 'student':
        news_qs = news_qs.filter(is_published=True)

    for n in news_qs:
        data.append({
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'created_at': n.created_at.isoformat() if n.created_at else '',
            'is_published': n.is_published,
            'category': n.category,
            'image_url': n.image_url,
            'video_url': n.video_url,
            'link': n.link,
            'views_count': n.views_count,
        })
    return Response(data)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def news_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        news = News.objects.get(id=pk)
    except News.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)

    if role == 'student' and not news.is_published:
        return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'GET':
        # +1 до views
        news.views_count += 1
        news.save()
        return Response({
            'id': news.id,
            'title': news.title,
            'content': news.content,
            'created_at': news.created_at.isoformat() if news.created_at else '',
            'is_published': news.is_published,
            'category': news.category,
            'image_url': news.image_url,
            'video_url': news.video_url,
            'link': news.link,
            'views_count': news.views_count,
        })
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        news.title = request.data.get('title', news.title)
        news.content = request.data.get('content', news.content)
        news.category = request.data.get('category', news.category)

        is_published_raw = request.data.get('is_published', news.is_published)
        if isinstance(is_published_raw, bool):
            is_published = is_published_raw
        else:
            is_published = str(is_published_raw).lower() in ('true', '1', 'yes')
        if is_published != news.is_published:
            news.is_published = is_published
            news.published_at = timezone.now() if is_published else None

        image_url = request.data.get('image_url', news.image_url)
        image_file = request.FILES.get('image_file')
        if image_file:
            safe_name = get_valid_filename(getattr(image_file, 'name', 'image'))
            stored_path = default_storage.save(f"news_images/{safe_name}", image_file)
            image_url = default_storage.url(stored_path)
        news.image_url = image_url

        news.video_url = request.data.get('video_url', news.video_url)
        news.link = request.data.get('link', news.link)
        news.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        news.delete()
        return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def news_view(request, pk):
    try:
        news = News.objects.get(id=pk)
    except News.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)

    role = _effective_role(getattr(request, 'user', None))
    if role == 'student' and not news.is_published:
        return Response({'detail': 'Forbidden'}, status=403)

    news.views_count = (news.views_count or 0) + 1
    news.save(update_fields=['views_count'])
    return Response({'success': True})


# ===== EXTRA NEWS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def extra_news_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
@permission_classes([IsAuthenticated])
def extra_news_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)
    try:
        extra_news = ExtraNews.objects.get(id=pk)
    except ExtraNews.DoesNotExist:
        return Response({'success': False, 'error': 'Новина не знайдена'}, status=404)
    if request.method == 'GET':
        return Response({'id': extra_news.id, 'title': extra_news.title, 'description': extra_news.description,
                         'media_type': extra_news.media_type})
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        extra_news.title = request.data.get('title', extra_news.title)
        extra_news.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        extra_news.delete()
        return Response({'success': True})


# ===== CHATS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chats_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        type_raw = str(request.data.get('type', '') or '').strip().lower() or 'private'
        if type_raw not in ('private', 'group'):
            return Response({'success': False, 'error': 'Некоректний тип чату'}, status=400)

        if type_raw == 'private':
            participant_id = request.data.get('participant_id')
            if not participant_id:
                return Response({'success': False, 'error': 'participant_id обовʼязковий'}, status=400)
            try:
                other = User.objects.get(id=int(participant_id))
            except (User.DoesNotExist, ValueError, TypeError):
                return Response({'success': False, 'error': 'Користувач не знайдений'}, status=404)

            # Find existing 1:1 chat
            existing = (
                Chat.objects.filter(type='private', participants__user=request.user)
                .filter(participants__user=other)
                .distinct()
                .first()
            )
            if existing:
                return Response({'success': True, 'chat': {'id': existing.id}}, status=200)

            chat = Chat.objects.create(type='private', name=None, created_by=request.user)
            ChatParticipant.objects.get_or_create(chat=chat, user=request.user)
            ChatParticipant.objects.get_or_create(chat=chat, user=other)
            return Response({'success': True, 'chat': {'id': chat.id}}, status=201)

        # group chat
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)

        name = str(request.data.get('name', '') or '').strip() or None
        participant_ids = request.data.get('participant_ids')
        if not isinstance(participant_ids, list) or len(participant_ids) == 0:
            return Response({'success': False, 'error': 'participant_ids має бути непорожнім списком'}, status=400)

        chat = Chat.objects.create(type='group', name=name, created_by=request.user)
        ChatParticipant.objects.get_or_create(chat=chat, user=request.user)
        for pid in participant_ids:
            try:
                u = User.objects.get(id=int(pid))
                ChatParticipant.objects.get_or_create(chat=chat, user=u)
            except Exception:
                continue

        return Response({'success': True, 'chat': {'id': chat.id, 'name': chat.name}}, status=201)

    chats_qs = Chat.objects.all()
    if role not in ('admin', 'superadmin'):
        chats_qs = chats_qs.filter(participants__user=request.user).distinct()

    result = []
    for c in chats_qs.order_by('-created_at'):
        participants = (
            User.objects.filter(chat_participations__chat=c)
            .only('id', 'name', 'email')
            .all()
        )
        result.append({
            'id': c.id,
            'name': c.name,
            'type': c.type,
            'participants': [{'id': u.id, 'name': u.name, 'email': u.email} for u in participants],
        })
    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def chat_detail(request, pk):
    try:
        chat = Chat.objects.get(id=pk)
    except Chat.DoesNotExist:
        return Response({'success': False, 'error': 'Чат не знайдений'}, status=404)

    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin'):
        is_participant = ChatParticipant.objects.filter(chat=chat, user=request.user).exists()
        if not is_participant:
            return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'GET':
        return Response({'id': chat.id, 'name': chat.name, 'type': chat.type})
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        chat.name = request.data.get('name', chat.name)
        chat.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        chat.delete()
        return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def chat_messages(request, pk):
    try:
        chat = Chat.objects.get(id=pk)
    except Chat.DoesNotExist:
        return Response({'success': False, 'error': 'Чат не знайдений'}, status=404)

    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin'):
        is_participant = ChatParticipant.objects.filter(chat=chat, user=request.user).exists()
        if not is_participant:
            return Response({'detail': 'Forbidden'}, status=403)

    if request.method == 'POST':
        content = str(request.data.get('content', '') or '')

        files = []
        try:
            files = request.FILES.getlist('files')
        except Exception:
            files = []

        if not content.strip() and len(files) == 0:
            return Response({'success': False, 'error': 'Повідомлення порожнє'}, status=400)

        # Ensure sender is a participant (helps keep chats consistent for admins too).
        try:
            ChatParticipant.objects.get_or_create(chat=chat, user=request.user)
        except Exception:
            pass

        message = ChatMessage.objects.create(chat=chat, sender=request.user, content=content)

        for f in files:
            safe_name = get_valid_filename(getattr(f, 'name', 'file'))
            stored_path = default_storage.save(f"chat_attachments/{chat.id}/{message.id}/{safe_name}", f)
            url = f"{settings.MEDIA_URL}{stored_path}"
            content_type = str(getattr(f, 'content_type', '') or '').lower()
            att_type = 'file'
            if content_type.startswith('image/'):
                att_type = 'image'
            elif content_type.startswith('video/'):
                att_type = 'video'

            ChatMessageAttachment.objects.create(
                message=message,
                type=att_type,
                name=safe_name,
                url=url,
                size=str(getattr(f, 'size', '') or ''),
            )

        # Notify other participants about a new message.
        try:
            other_users = (
                User.objects.filter(chat_participations__chat=chat)
                .exclude(id=request.user.id)
                .distinct()
            )
            link = f"/dashboard/chat?chatId={chat.id}"
            preview = content.strip() or 'Вкладення'
            if len(preview) > 200:
                preview = preview[:200] + '…'
            for u in other_users:
                Notification.objects.create(
                    user=u,
                    type='message',
                    title='Нове повідомлення',
                    message=preview,
                    link=link,
                )
        except Exception:
            pass

        return Response({'success': True, 'message': {'id': message.id}}, status=201)

    messages = chat.messages.select_related('sender').all()
    payload = []
    for m in messages:
        attachments = []
        try:
            attachments = [
                {
                    'id': a.id,
                    'type': a.type,
                    'name': a.name,
                    'url': a.url,
                    'size': a.size,
                }
                for a in m.attachments.all()
            ]
        except Exception:
            attachments = []

        payload.append(
            {
                'id': m.id,
                'sender_id': m.sender_id,
                'sender': m.sender.name,
                'content': m.content,
                'created_at': m.created_at.isoformat() if m.created_at else '',
                'attachments': attachments,
            }
        )

    return Response(payload)


# ===== POLLS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def polls_list(request):
    role = _effective_role(getattr(request, 'user', None))

    def _parse_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ('1', 'true', 'yes', 'y', 'on'):
            return True
        if s in ('0', 'false', 'no', 'n', 'off', ''):
            return False
        return default

    def _parse_iso_date(value):
        if value is None:
            return None
        if isinstance(value, date):
            return value
        s = str(value).strip()
        if not s:
            return None
        try:
            return datetime.datetime.strptime(s[:10], '%Y-%m-%d').date()
        except Exception:
            return None

    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        title = request.data.get('title')
        options = request.data.get('options', [])
        target_type = request.data.get('targetType', 'all')
        group_ids = request.data.get('groupIds', [])
        is_anonymous = _parse_bool(request.data.get('isAnonymous', False), default=False)
        is_multiple_choice = _parse_bool(request.data.get('isMultipleChoice', False), default=False)
        ends_at = _parse_iso_date(request.data.get('endsAt'))

        # Валідація
        if not title or not isinstance(options, list) or len(options) < 2 or not ends_at:
            return Response({'success': False, 'error': 'Перевірте всі обовʼязкові поля'}, status=400)
        # Дата не раніше сьогодні
        if ends_at < date.today():
            return Response({'success': False, 'error': 'Дата закриття некоректна'}, status=400)

        poll = Poll.objects.create(
            title=title,
            description=request.data.get('description',''),
            target_type=target_type,
            is_anonymous=is_anonymous,
            is_multiple_choice=is_multiple_choice,
            ends_at=ends_at
        )
        # Store legacy single target_group (first), but notifications can be sent to multiple groups.
        normalized_group_ids: list[int] = []
        if isinstance(group_ids, list):
            for gid in group_ids:
                try:
                    normalized_group_ids.append(int(gid))
                except Exception:
                    continue
        elif group_ids is not None and str(group_ids).strip():
            try:
                normalized_group_ids = [int(group_ids)]
            except Exception:
                normalized_group_ids = []

        if target_type == "group" and normalized_group_ids:
            try:
                poll.target_group = Group.objects.get(id=int(normalized_group_ids[0]))
                poll.save(update_fields=['target_group'])
            except Exception:
                pass

        for o in options:
            text = (o.get('text') if isinstance(o, dict) else None) or ''
            if str(text).strip():
                PollOption.objects.create(poll=poll, text=str(text).strip())

        # Notifications to students
        try:
            student_ids: set[int] = set()

            if target_type == 'all':
                student_ids = set(User.objects.filter(role='student').values_list('id', flat=True))
            elif target_type == 'group' and normalized_group_ids:
                student_ids = set(
                    User.objects.filter(role='student', group_id__in=normalized_group_ids)
                    .values_list('id', flat=True)
                )
                extra_ids = set(
                    GroupStudent.objects.filter(group_id__in=normalized_group_ids)
                    .values_list('student_id', flat=True)
                )
                student_ids.update(extra_ids)

            if student_ids:
                link = f"/dashboard/notifications?pollId={poll.id}"
                Notification.objects.bulk_create(
                    [
                        Notification(
                            user_id=sid,
                            type='poll',
                            title=f"Опитування: {poll.title}",
                            message=(poll.description or '')[:500],
                            link=link,
                        )
                        for sid in student_ids
                    ]
                )
        except Exception:
            pass

        return Response({'success': True, 'pollId': poll.id})

    # GET — список опитувань (простий респонс, додай потрібні поля)
    result = []
    polls_qs = Poll.objects.all().order_by('-created_at')
    if role == 'student':
        polls_qs = polls_qs.exclude(status='draft')
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if effective_group_id:
            polls_qs = polls_qs.filter(
                models.Q(target_type='all') |
                models.Q(target_type='group', target_group_id=effective_group_id)
            )
        else:
            polls_qs = polls_qs.filter(target_type='all')

    for poll in polls_qs:
        voters_count = (
            PollVote.objects
            .filter(option__poll=poll)
            .values('student_id')
            .distinct()
            .count()
        )
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
            'votersCount': voters_count,
        })
    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def poll_detail(request, pk):
    """
    Детальна інформація про опитування + всі варіанти і кількість голосів
    """
    try:
        poll = Poll.objects.select_related('target_group').get(id=pk)

        if request.method == 'DELETE':
            forbidden = _require_roles(request, ('admin', 'superadmin'))
            if forbidden:
                return forbidden
            poll.delete()
            return Response({'success': True})

        if request.method == 'PUT':
            forbidden = _require_roles(request, ('admin', 'superadmin'))
            if forbidden:
                return forbidden

            poll.title = request.data.get('title', poll.title)
            poll.description = request.data.get('description', poll.description)
            poll.target_type = request.data.get('targetType', poll.target_type)
            def _parse_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                s = str(value).strip().lower()
                if s in ('1', 'true', 'yes', 'y', 'on'):
                    return True
                if s in ('0', 'false', 'no', 'n', 'off', ''):
                    return False
                return default

            poll.is_anonymous = _parse_bool(request.data.get('isAnonymous', poll.is_anonymous), default=bool(poll.is_anonymous))
            poll.is_multiple_choice = _parse_bool(request.data.get('isMultipleChoice', poll.is_multiple_choice), default=bool(poll.is_multiple_choice))

            ends_at = request.data.get('endsAt')
            if ends_at is not None and str(ends_at).strip():
                try:
                    poll.ends_at = datetime.datetime.strptime(str(ends_at)[:10], '%Y-%m-%d').date()
                except Exception:
                    pass

            group_ids = request.data.get('groupIds', [])
            if poll.target_type == 'group' and isinstance(group_ids, list) and len(group_ids) > 0:
                try:
                    poll.target_group = Group.objects.get(id=int(group_ids[0]))
                except Exception:
                    poll.target_group = None
            else:
                poll.target_group = None

            poll.save()

            options = request.data.get('options', [])
            if isinstance(options, list) and len(options) >= 2:
                poll.options.all().delete()
                for o in options:
                    text = (o.get('text') if isinstance(o, dict) else None) or ''
                    if str(text).strip():
                        PollOption.objects.create(poll=poll, text=str(text).strip())

            return Response({'success': True})

        options = poll.options.all()
        options_data = []
        for option in options:
            votes_count = option.votes.count() if hasattr(option, 'votes') else 0
            options_data.append({
                'id': option.id,
                'text': option.text,
                'votes': votes_count,
            })

        if request.method == 'GET':
            role = _effective_role(getattr(request, 'user', None))
            if role == 'student':
                # Allow access only for intended recipients.
                can = False
                if poll.target_type == 'all':
                    can = True
                else:
                    try:
                        student = request.user
                        group_ids = []
                        if getattr(student, 'group_id', None):
                            group_ids.append(int(student.group_id))
                        group_ids.extend(
                            list(
                                GroupStudent.objects.filter(student_id=student.id)
                                .values_list('group_id', flat=True)
                            )
                        )
                        if poll.target_group_id and int(poll.target_group_id) in [int(x) for x in group_ids if x is not None]:
                            can = True
                    except Exception:
                        can = False

                    # If poll was delivered via notification, allow it even when target_group is legacy/single.
                    if not can:
                        try:
                            can = Notification.objects.filter(
                                user=request.user,
                                type='poll',
                                link__contains=f"pollId={poll.id}",
                            ).exists()
                        except Exception:
                            can = False

                if not can:
                    return Response({'detail': 'Forbidden'}, status=403)

        has_voted = False
        try:
            current_user = getattr(request, 'user', None)
            if current_user and getattr(current_user, 'id', None):
                has_voted = PollVote.objects.filter(option__poll=poll, student_id=current_user.id).exists()
        except Exception:
            has_voted = False

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
            'hasVoted': bool(has_voted),
            'endsAt': poll.ends_at.isoformat(),
            'createdAt': poll.created_at.isoformat() if poll.created_at else '',
        })
    except Poll.DoesNotExist:
        return Response({'success': False, 'error': 'Опитування не знайдене'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def poll_vote(request, pk):
    """
    Додати голосування: pk - option.id, student_id в тілі
    """
    try:
        option = PollOption.objects.select_related('poll').get(id=pk)
        role = _effective_role(getattr(request, 'user', None))
        if role != 'student':
            return Response({'detail': 'Forbidden'}, status=403)
        student = request.user

        poll = option.poll
        if poll.status != 'active':
            return Response({'success': False, 'error': 'Опитування закрите'}, status=400)
        if poll.ends_at and poll.ends_at < date.today():
            return Response({'success': False, 'error': 'Термін опитування минув'}, status=400)

        # Single-choice: block if student already voted in this poll.
        if not bool(getattr(poll, 'is_multiple_choice', False)):
            if PollVote.objects.filter(option__poll=poll, student=student).exists():
                return Response({'success': False, 'error': 'Ви вже голосували в цьому опитуванні'}, status=400)

        # Захист від подвійного голосу за цей варіант:
        if PollVote.objects.filter(option=option, student=student).exists():
            return Response({'success': False, 'error': 'Ви вже голосували за цей варіант'}, status=400)

        vote = PollVote.objects.create(option=option, student=student)
        return Response({'success': True, 'vote': {'id': vote.id}}, status=201)
    except (PollOption.DoesNotExist, User.DoesNotExist):
        return Response({'success': False, 'error': 'Not found (option or student)'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def poll_close(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    try:
        poll = Poll.objects.get(id=pk)
    except Poll.DoesNotExist:
        return Response({'success': False, 'error': 'Опитування не знайдене'}, status=404)
    poll.status = 'closed'
    poll.save(update_fields=['status'])
    return Response({'success': True})

# ===== COURSES =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def courses_list(request):
    role = _effective_role(getattr(request, 'user', None))

    def _parse_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ('1', 'true', 'yes', 'y', 'on'):
            return True
        if s in ('0', 'false', 'no', 'n', 'off', ''):
            return False
        return default

    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
            is_published=_parse_bool(request.data.get('is_published', False), default=False)
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
    if role == 'student':
        courses = courses.filter(is_published=True)
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if effective_group_id:
            courses = courses.filter(models.Q(group__isnull=True) | models.Q(group_id=effective_group_id))
        else:
            courses = courses.filter(group__isnull=True)
    result = []

    for course in courses:
        course_data = {
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'thumbnail': course.thumbnail,
            'is_published': course.is_published,
            'created_at': course.created_at.isoformat() if getattr(course, 'created_at', None) else '',
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
@permission_classes([IsAuthenticated])
def course_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        course = Course.objects.select_related('group', 'subject').get(id=pk)
    except Course.DoesNotExist:
        return Response({'success': False, 'error': 'Курс не знайдений'}, status=404)

    if role == 'student':
        if not course.is_published:
            return Response({'detail': 'Forbidden'}, status=403)
        effective_group_id = getattr(request.user, 'group_id', None)
        if not effective_group_id:
            effective_group_id = (
                GroupStudent.objects.filter(student_id=request.user.id)
                .values_list('group_id', flat=True)
                .first()
            )
        if course.group_id and effective_group_id != course.group_id:
            return Response({'detail': 'Forbidden'}, status=403)

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
                    'is_correct': o.is_correct if role in ('admin', 'superadmin') else None,
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
            'created_at': course.created_at.isoformat() if getattr(course, 'created_at', None) else '',
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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)

        def _parse_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in ('1', 'true', 'yes', 'y', 'on'):
                return True
            if s in ('0', 'false', 'no', 'n', 'off', ''):
                return False
            return default

        course.title = request.data.get('title', course.title)
        course.description = request.data.get('description', course.description)
        course.thumbnail = request.data.get('thumbnail', course.thumbnail)
        course.is_published = _parse_bool(request.data.get('is_published', course.is_published), default=bool(course.is_published))

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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        course.delete()
        return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def course_add_material(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
        is_required=(
            (str(request.data.get('is_required')).strip().lower() not in ('0', 'false', 'no', 'off'))
            if request.data.get('is_required') is not None
            else True
        )
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
@permission_classes([IsAuthenticated])
def course_remove_material(request, course_pk, material_pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    """Видалити матеріал з курсу"""
    try:
        material = CourseMaterial.objects.get(id=material_pk, course_id=course_pk)
        material.delete()
        return Response({'success': True})
    except CourseMaterial.DoesNotExist:
        return Response({'success': False, 'error': 'Матеріал не знайдений'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def course_add_test(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
def course_remove_test(request, course_pk, test_pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
    """Видалити тест з курсу"""
    try:
        test = CourseTest.objects.get(id=test_pk, course_id=course_pk)
        test.delete()
        return Response({'success': True})
    except CourseTest.DoesNotExist:
        return Response({'success': False, 'error': 'Тест не знайдений'}, status=404)
# ===== TEAMS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teams_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        name = (request.data.get('name', '') or '').strip()
        if not name:
            return Response({'success': False, 'error': 'Назва команди обов\'язкова'}, status=400)
        team = Team.objects.create(
            name=name,
            description=(request.data.get('description', '') or '').strip(),
            color=(request.data.get('color', '#FF9A00') or '#FF9A00').strip(),
        )
        return Response({'success': True, 'team': {'id': team.id, 'name': team.name}}, status=201)

    # GET - повертаємо команди зі студентами
    teams = Team.objects.all().order_by('-created_at')
    team_ids = list(teams.values_list('id', flat=True))

    memberships = (
        TeamMember.objects
        .select_related('student', 'team')
        .filter(team_id__in=team_ids)
        .all()
    )
    student_ids = list({int(m.student_id) for m in memberships})
    points_rows = (
        StudentPoint.objects
        .filter(student_id__in=student_ids)
        .values('student_id')
        .annotate(total=Sum('points'))
    )
    points_by_student_id = {int(r['student_id']): int(r.get('total') or 0) for r in points_rows}

    members_by_team_id: dict[int, list[dict]] = {}
    for m in memberships:
        members_by_team_id.setdefault(int(m.team_id), []).append(
            {
                'id': m.student.id,
                'name': m.student.name,
                'email': m.student.email,
                'points': points_by_student_id.get(int(m.student_id), 0),
            }
        )

    result = []
    for team in teams:
        result.append(
            {
                'id': team.id,
                'name': team.name,
                'description': team.description or '',
                'color': team.color,
                'total_points': int(getattr(team, 'total_points', 0) or 0),
                'created_at': team.created_at.isoformat() if team.created_at else '',
                'members': members_by_team_id.get(int(team.id), []),
            }
        )

    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def team_add_members(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
def team_remove_member(request, pk):
    forbidden = _require_roles(request, ('admin', 'superadmin'))
    if forbidden:
        return forbidden
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
@permission_classes([IsAuthenticated])
def team_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)
    try:
        team = Team.objects.get(id=pk)
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)
    if request.method == 'GET':
        return Response(
            {
                'id': team.id,
                'name': team.name,
                'description': team.description or '',
                'color': team.color,
                'total_points': int(getattr(team, 'total_points', 0) or 0),
                'created_at': team.created_at.isoformat() if team.created_at else '',
            }
        )
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        team.name = (request.data.get('name', team.name) or team.name).strip()
        team.description = request.data.get('description', team.description)
        color = request.data.get('color', team.color)
        if isinstance(color, str) and color.strip():
            team.color = color.strip()
        team.save(update_fields=['name', 'description', 'color'])
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        team.delete()
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)
    try:
        team = Team.objects.get(id=pk)
        members = TeamMember.objects.filter(team=team)
        return Response([{'id': m.student.id, 'name': m.student.name, 'email': m.student.email} for m in members])
    except Team.DoesNotExist:
        return Response({'success': False, 'error': 'Команда не знайдена'}, status=404)


# ===== PUZZLES =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def puzzles_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
                'created_at': puzzle.created_at.isoformat() if puzzle.created_at else ''
            }
        }, status=201)

    # GET - для студентів не показуємо вже розв'язані загадки
    puzzles = Puzzle.objects.filter(is_active=True)
    if role == 'student':
        solved_subquery = StudentPoint.objects.filter(
            student=request.user,
            source_id=models.OuterRef('id'),
        ).filter(
            models.Q(source_type__iexact='puzzle') |
            models.Q(source_type__icontains='puzz') |
            models.Q(description__istartswith='Загадка:')
        )
        puzzles = puzzles.annotate(_is_solved=models.Exists(solved_subquery)).filter(_is_solved=False)
    return Response([{
        'id': p.id,
        'title': p.title,
        'question': p.question,
        'hint': p.hint,
        'type': p.type,
        'difficulty': p.difficulty,
        'points': p.points,
        'solved_by': p.solved_by,
        'created_at': p.created_at.isoformat() if p.created_at else ''
    } for p in puzzles])


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def puzzle_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    try:
        puzzle = Puzzle.objects.get(id=pk)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)

    if request.method == 'GET':
        payload = {
            'id': puzzle.id,
            'title': puzzle.title,
            'question': puzzle.question,
            'hint': puzzle.hint,
            'type': puzzle.type,
            'difficulty': puzzle.difficulty,
            'points': puzzle.points,
            'solved_by': puzzle.solved_by,
        }
        if role in ('admin', 'superadmin'):
            payload['answer'] = puzzle.answer
        return Response(payload)

    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
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
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        puzzle.delete()
        return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def puzzle_answer(request, pk):
    """Перевірка відповіді на загадку"""
    role = _effective_role(getattr(request, 'user', None))
    if role != 'student':
        return Response({'detail': 'Forbidden'}, status=403)
    try:
        puzzle = Puzzle.objects.get(id=pk)
    except Puzzle.DoesNotExist:
        return Response({'success': False, 'error': 'Головоломка не знайдена'}, status=404)

    answer = request.data.get('answer', '').strip().lower()
    correct_answer = puzzle.answer.strip().lower()

    if answer == correct_answer:
        # Prevent double scoring for the same puzzle by the same student.
        already_scored = StudentPoint.objects.filter(
            student=request.user,
            source_type='puzzle',
            source_id=puzzle.id,
        ).exists()

        if already_scored:
            return Response({
                'success': True,
                'correct': True,
                'already_solved': True,
                'points': 0,
                'message': 'Правильно! Ви вже отримали бали за цю загадку.',
            })

        puzzle.solved_by += 1
        puzzle.save()

        StudentPoint.objects.create(
            student=request.user,
            points=int(getattr(puzzle, 'points', 0) or 0),
            source_type='puzzle',
            source_id=puzzle.id,
            description=f'Загадка: {puzzle.title}',
        )

        membership = TeamMember.objects.filter(student=request.user).select_related('team').first()
        if membership and membership.team:
            membership.team.total_points = (membership.team.total_points or 0) + int(getattr(puzzle, 'points', 0) or 0)
            membership.team.save(update_fields=['total_points'])

        return Response({
            'success': True,
            'correct': True,
            'already_solved': False,
            'points': puzzle.points,
            'message': f'Правильно! Ви отримали {puzzle.points} балів!'
        })

    return Response({
        'success': True,
        'correct': False,
        'already_solved': False,
        'message': 'Неправильна відповідь. Спробуйте ще раз!'
    }, status=200)


# ===== LEARNING MATERIALS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def learning_materials_list(request):
    role = _effective_role(getattr(request, 'user', None))

    def _parse_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ('1', 'true', 'yes', 'y', 'on'):
            return True
        if s in ('0', 'false', 'no', 'n', 'off', ''):
            return False
        return default

    def _parse_int_list(raw):
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            items = list(raw)
        else:
            s = str(raw).strip()
            if not s:
                return []
            try:
                items = json.loads(s)
            except Exception:
                items = [part.strip() for part in s.split(',') if part.strip()]

        result = []
        for item in items:
            try:
                result.append(int(item))
            except Exception:
                continue
        return list(dict.fromkeys(result))

    def _student_group_ids(student: User) -> list[int]:
        ids: list[int] = []
        try:
            if getattr(student, 'group_id', None):
                ids.append(int(student.group_id))
        except Exception:
            pass
        try:
            extra = list(
                GroupStudent.objects.filter(student_id=student.id).values_list('group_id', flat=True)
            )
            ids.extend([int(x) for x in extra if x is not None])
        except Exception:
            pass
        return list(dict.fromkeys(ids))

    def _material_payload(m: LearningMaterial):
        groups_payload = []
        try:
            links = list(m.group_links.select_related('group').all())
            for link in links:
                if not link.group:
                    continue
                groups_payload.append(
                    {
                        'id': link.group.id,
                        'name': link.group.name,
                        'color': link.group.color,
                        'is_published': bool(link.is_published),
                    }
                )
        except Exception:
            groups_payload = []

        group_payload = None
        if getattr(m, 'group', None):
            group_payload = {
                'id': m.group.id,
                'name': m.group.name,
                'color': m.group.color,
            }

        return {
            'id': m.id,
            'title': m.title,
            'type': m.type,
            'kind': getattr(m, 'kind', None) or 'video',
            'content_text': getattr(m, 'content_text', None) or '',
            'description': m.description,
            'created_at': m.created_at.isoformat() if m.created_at else '',
            'is_published': bool(m.is_published),
            'folder': (
                {
                    'id': m.folder.id,
                    'name': m.folder.name,
                }
                if getattr(m, 'folder', None)
                else None
            ),
            'subject': (
                {
                    'id': m.subject.id,
                    'name': m.subject.name,
                    'short_name': m.subject.short_name,
                    'color': m.subject.color,
                }
                if m.subject
                else None
            ),
            'group': group_payload,
            'groups': groups_payload,
            'attachments': [
                {
                    'id': a.id,
                    'type': a.type,
                    'name': a.name,
                    'url': a.url,
                    'file_size': a.file_size,
                }
                for a in getattr(m, 'attachments', []).all()
            ],
        }

    if request.method == 'POST':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        title = (request.data.get('title', '') or '').strip()
        if not title:
            return Response({'success': False, 'error': 'Назва обов\'язкова'}, status=400)

        description = (request.data.get('description', '') or '').strip()
        material_type = (request.data.get('type', 'material') or 'material').strip()
        kind = (request.data.get('kind', '') or '').strip().lower() or 'video'
        if kind not in ('video', 'document', 'article', 'book'):
            return Response({'success': False, 'error': 'Некоректний тип матеріалу'}, status=400)

        group_ids = _parse_int_list(request.data.get('group_ids'))
        if not group_ids:
            # Backward compatibility (single group_id)
            legacy_group_id = request.data.get('group_id')
            try:
                if legacy_group_id is not None and str(legacy_group_id).strip() != '':
                    group_ids = [int(legacy_group_id)]
            except Exception:
                group_ids = []

        if not group_ids:
            return Response({'success': False, 'error': 'Оберіть хоча б одну групу'}, status=400)

        subject = None
        subject_id = request.data.get('subject_id')
        if subject_id is not None and str(subject_id).strip() != '':
            try:
                subject = Subject.objects.get(id=int(subject_id))
            except Exception:
                subject = None

        folder = None
        folder_id = request.data.get('folder_id')
        if folder_id is not None and str(folder_id).strip() != '':
            try:
                folder = LearningMaterialFolder.objects.get(id=int(folder_id))
            except Exception:
                folder = None

        if folder is None:
            return Response({'success': False, 'error': 'Оберіть папку'}, status=400)

        is_published = _parse_bool(request.data.get('is_published', True), default=True)

        content_text = (request.data.get('content_text', '') or '').strip()
        video_url = (request.data.get('video_url', '') or '').strip()
        link_url = (request.data.get('link_url', '') or '').strip()
        file_obj = request.FILES.get('file')

        if kind == 'article':
            if not content_text:
                return Response({'success': False, 'error': 'Текст статті обов\'язковий'}, status=400)
        elif kind == 'video':
            if not video_url:
                return Response({'success': False, 'error': 'Посилання на відео обов\'язкове'}, status=400)
        elif kind in ('document', 'book'):
            if not file_obj and not link_url:
                return Response({'success': False, 'error': 'Потрібен файл або посилання'}, status=400)

        # Keep legacy FK for backwards compatibility (first group)
        legacy_group = None
        try:
            legacy_group = Group.objects.get(id=int(group_ids[0]))
        except Exception:
            legacy_group = None

        material = LearningMaterial.objects.create(
            title=title,
            description=description,
            type=material_type,
            kind=kind,
            content_text=content_text if kind == 'article' else None,
            group=legacy_group,
            folder=folder,
            subject=subject,
            is_published=is_published,
        )

        group_published_raw = request.data.get('group_published')
        group_published = {}
        if group_published_raw is not None:
            try:
                items = group_published_raw
                if not isinstance(items, list):
                    items = json.loads(str(group_published_raw))
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        gid = item.get('group_id')
                        try:
                            gid_int = int(gid)
                        except Exception:
                            continue
                        group_published[gid_int] = _parse_bool(item.get('is_published', True), default=True)
            except Exception:
                group_published = {}

        links = []
        for gid in group_ids:
            links.append(
                LearningMaterialGroup(
                    material=material,
                    group_id=gid,
                    is_published=group_published.get(gid, True),
                )
            )
        LearningMaterialGroup.objects.bulk_create(links, ignore_conflicts=True)

        # Build attachment based on kind
        if kind == 'video':
            a_type = 'youtube' if ('youtube.com' in video_url or 'youtu.be' in video_url) else 'video'
            LearningMaterialAttachment.objects.create(
                material=material,
                type=a_type,
                name='Video',
                url=video_url,
                file_size=None,
            )
        elif kind in ('document', 'book'):
            if file_obj:
                safe_name = get_valid_filename(getattr(file_obj, 'name', 'file'))
                stored_path = default_storage.save(f"materials/{material.id}/{safe_name}", file_obj)
                url = default_storage.url(stored_path)
                LearningMaterialAttachment.objects.create(
                    material=material,
                    type='document' if kind == 'document' else 'file',
                    name=safe_name,
                    url=url,
                    file_size=str(getattr(file_obj, 'size', '') or '') or None,
                )
            elif link_url:
                LearningMaterialAttachment.objects.create(
                    material=material,
                    type='document' if kind == 'document' else 'file',
                    name='Link',
                    url=link_url,
                    file_size=None,
                )

        # Create notifications for students in target groups
        try:
            student_ids = set(
                User.objects.filter(role='student', group_id__in=group_ids).values_list('id', flat=True)
            )
            extra_ids = set(
                GroupStudent.objects.filter(group_id__in=group_ids).values_list('student_id', flat=True)
            )
            student_ids.update(extra_ids)
            notifications = []
            for sid in student_ids:
                notifications.append(
                    Notification(
                        user_id=sid,
                        type='material',
                        title=f"Новий матеріал: {material.title}",
                        message=(material.description or '')[:500],
                        link=f"/dashboard/materials?materialId={material.id}",
                    )
                )
            if notifications:
                Notification.objects.bulk_create(notifications)
        except Exception:
            pass

        return Response({'success': True, 'material': {'id': material.id, 'title': material.title}}, status=201)

    materials = (
        LearningMaterial.objects
        .select_related('subject', 'group')
        .select_related('folder')
        .prefetch_related('attachments', 'group_links__group')
        .all()
    )

    folder_filter = request.query_params.get('folder_id')
    if folder_filter is not None and str(folder_filter).strip() != '':
        try:
            materials = materials.filter(folder_id=int(folder_filter))
        except Exception:
            pass

    if role == 'student':
        group_ids = _student_group_ids(request.user)
        materials = materials.filter(is_published=True)
        if group_ids:
            materials = materials.filter(
                (
                    models.Q(group_links__group_id__in=group_ids, group_links__is_published=True)
                    | models.Q(group_id__in=group_ids)
                    | models.Q(group_links__isnull=True, group_id__isnull=True)
                )
            ).distinct()
        else:
            materials = materials.filter(group_links__isnull=True, group_id__isnull=True)

    payload = [_material_payload(m) for m in materials.order_by('-created_at')]
    return Response(payload)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def learning_material_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)

    try:
        material = (
            LearningMaterial.objects
            .select_related('subject', 'group', 'folder')
            .prefetch_related('attachments', 'group_links', 'group_links__group')
            .get(id=pk)
        )
    except LearningMaterial.DoesNotExist:
        return Response({'success': False, 'error': 'Матеріал не знайдений'}, status=404)

    def _student_group_ids(student: User) -> list[int]:
        ids: list[int] = []
        try:
            if getattr(student, 'group_id', None):
                ids.append(int(student.group_id))
        except Exception:
            pass
        try:
            extra = list(
                GroupStudent.objects.filter(student_id=student.id).values_list('group_id', flat=True)
            )
            ids.extend([int(x) for x in extra if x is not None])
        except Exception:
            pass
        return list(dict.fromkeys(ids))

    def _student_can_access(m: LearningMaterial, student: User) -> bool:
        if not bool(getattr(m, 'is_published', False)):
            return False
        gids = _student_group_ids(student)
        # Global (no group bindings)
        if (not getattr(m, 'group_id', None)) and (not m.group_links.exists()):
            return True
        # Legacy FK
        if getattr(m, 'group_id', None) and gids and int(m.group_id) in gids:
            return True
        # Multi-group links
        if gids and m.group_links.filter(group_id__in=gids, is_published=True).exists():
            return True
        return False

    if role == 'student' and not _student_can_access(material, request.user):
        return Response({'detail': 'Forbidden'}, status=403)
    if request.method == 'GET':
        groups_payload = []
        try:
            for link in material.group_links.select_related('group').all():
                if not link.group:
                    continue
                groups_payload.append(
                    {
                        'id': link.group.id,
                        'name': link.group.name,
                        'color': link.group.color,
                        'is_published': bool(link.is_published),
                    }
                )
        except Exception:
            groups_payload = []

        return Response(
            {
                'id': material.id,
                'title': material.title,
                'description': material.description,
                'type': material.type,
                'kind': getattr(material, 'kind', None) or 'video',
                'content_text': getattr(material, 'content_text', None) or '',
                'created_at': material.created_at.isoformat() if material.created_at else '',
                'is_published': bool(material.is_published),
                'folder': (
                    {
                        'id': material.folder.id,
                        'name': material.folder.name,
                    }
                    if getattr(material, 'folder', None)
                    else None
                ),
                'subject': (
                    {
                        'id': material.subject.id,
                        'name': material.subject.name,
                        'short_name': material.subject.short_name,
                        'color': material.subject.color,
                    }
                    if material.subject
                    else None
                ),
                'group': (
                    {
                        'id': material.group.id,
                        'name': material.group.name,
                        'color': material.group.color,
                    }
                    if material.group
                    else None
                ),
                'groups': groups_payload,
                'attachments': [
                    {
                        'id': a.id,
                        'type': a.type,
                        'name': a.name,
                        'url': a.url,
                        'file_size': a.file_size,
                    }
                    for a in material.attachments.all()
                ],
            }
        )
    if request.method == 'PUT':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        prev_kind = getattr(material, 'kind', None) or 'video'

        material.title = (request.data.get('title', material.title) or material.title).strip()
        material.description = request.data.get('description', material.description)

        incoming_kind = request.data.get('kind', None)
        if incoming_kind is not None:
            k = (str(incoming_kind) or '').strip().lower()
            if k and k in ('video', 'document', 'article', 'book'):
                material.kind = k

        is_published_raw = request.data.get('is_published', material.is_published)
        if isinstance(is_published_raw, bool):
            material.is_published = is_published_raw
        else:
            material.is_published = str(is_published_raw).lower() in ('true', '1', 'yes')

        group_id = request.data.get('group_id')
        subject_id = request.data.get('subject_id')
        if group_id is not None:
            if str(group_id).strip() == '':
                material.group = None
            else:
                try:
                    material.group = Group.objects.get(id=int(group_id))
                except Exception:
                    pass
        if subject_id is not None:
            if str(subject_id).strip() == '':
                material.subject = None
            else:
                try:
                    material.subject = Subject.objects.get(id=int(subject_id))
                except Exception:
                    pass

        folder_id = request.data.get('folder_id', None)
        if folder_id is not None:
            if str(folder_id).strip() == '':
                return Response({'success': False, 'error': 'Папка обов\'язкова'}, status=400)
            try:
                material.folder = LearningMaterialFolder.objects.get(id=int(folder_id))
            except Exception:
                return Response({'success': False, 'error': 'Некоректна папка'}, status=400)

        # Groups (multi)
        group_ids_raw = request.data.get('group_ids', None)
        group_published_raw = request.data.get('group_published', None)
        if group_ids_raw is not None:
            def _parse_int_list(raw):
                if raw is None:
                    return []
                if isinstance(raw, (list, tuple)):
                    items = list(raw)
                else:
                    s = str(raw).strip()
                    if not s:
                        return []
                    try:
                        items = json.loads(s)
                    except Exception:
                        items = [part.strip() for part in s.split(',') if part.strip()]
                result = []
                for item in items:
                    try:
                        result.append(int(item))
                    except Exception:
                        continue
                return list(dict.fromkeys(result))

            group_ids = _parse_int_list(group_ids_raw)
            if not group_ids:
                return Response({'success': False, 'error': 'Оберіть хоча б одну групу'}, status=400)

            published_map = {}
            if group_published_raw is not None:
                try:
                    items = group_published_raw
                    if not isinstance(items, list):
                        items = json.loads(str(group_published_raw))
                    if isinstance(items, list):
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            gid = item.get('group_id')
                            try:
                                gid_int = int(gid)
                            except Exception:
                                continue
                            published_map[gid_int] = str(item.get('is_published', True)).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
                except Exception:
                    published_map = {}

            material.group_links.all().delete()
            LearningMaterialGroup.objects.bulk_create(
                [
                    LearningMaterialGroup(
                        material=material,
                        group_id=gid,
                        is_published=published_map.get(gid, True),
                    )
                    for gid in group_ids
                ],
                ignore_conflicts=True,
            )

            # legacy FK = first group
            try:
                material.group = Group.objects.get(id=int(group_ids[0]))
            except Exception:
                material.group = None

        # Content validation / update
        kind = getattr(material, 'kind', None) or 'video'
        content_text = (request.data.get('content_text', None) or '').strip() if request.data.get('content_text', None) is not None else None
        video_url = (request.data.get('video_url', None) or '').strip() if request.data.get('video_url', None) is not None else None
        link_url = (request.data.get('link_url', None) or '').strip() if request.data.get('link_url', None) is not None else None
        file_obj = request.FILES.get('file')

        kind_changed = kind != prev_kind

        if kind == 'article':
            if content_text is None:
                if kind_changed and not (getattr(material, 'content_text', None) or '').strip():
                    return Response({'success': False, 'error': 'Текст статті обов\'язковий'}, status=400)
            else:
                if not content_text:
                    return Response({'success': False, 'error': 'Текст статті обов\'язковий'}, status=400)
                material.content_text = content_text
        else:
            # Non-article: clear article content if kind changed.
            if kind_changed:
                material.content_text = None

        if kind == 'video':
            if video_url is not None:
                if not video_url:
                    return Response({'success': False, 'error': 'Посилання на відео обов\'язкове'}, status=400)
                material.attachments.all().delete()
                a_type = 'youtube' if ('youtube.com' in video_url or 'youtu.be' in video_url) else 'video'
                LearningMaterialAttachment.objects.create(
                    material=material,
                    type=a_type,
                    name='Video',
                    url=video_url,
                    file_size=None,
                )
            elif kind_changed and material.attachments.count() == 0:
                return Response({'success': False, 'error': 'Посилання на відео обов\'язкове'}, status=400)

        if kind in ('document', 'book'):
            if file_obj or (link_url is not None and link_url):
                material.attachments.all().delete()
                if file_obj:
                    safe_name = get_valid_filename(getattr(file_obj, 'name', 'file'))
                    stored_path = default_storage.save(f"materials/{material.id}/{safe_name}", file_obj)
                    url = default_storage.url(stored_path)
                    LearningMaterialAttachment.objects.create(
                        material=material,
                        type='document' if kind == 'document' else 'file',
                        name=safe_name,
                        url=url,
                        file_size=str(getattr(file_obj, 'size', '') or '') or None,
                    )
                else:
                    LearningMaterialAttachment.objects.create(
                        material=material,
                        type='document' if kind == 'document' else 'file',
                        name='Link',
                        url=link_url,
                        file_size=None,
                    )
            elif kind_changed and material.attachments.count() == 0:
                return Response({'success': False, 'error': 'Потрібен файл або посилання'}, status=400)

        material.save()
        return Response({'success': True})
    if request.method == 'DELETE':
        if role not in ('admin', 'superadmin'):
            return Response({'detail': 'Forbidden'}, status=403)
        material.delete()
        return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def learning_material_folders_list(request):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)

    # Mutations are admin-only
    if request.method == 'POST':
        forbidden = _require_roles(request, ('admin', 'superadmin'))
        if forbidden:
            return forbidden

        name = (request.data.get('name', '') or '').strip()
        if not name:
            return Response({'success': False, 'error': 'Назва папки обов\'язкова'}, status=400)
        folder = LearningMaterialFolder.objects.create(name=name)
        return Response({'success': True, 'folder': {'id': folder.id, 'name': folder.name}}, status=201)

    # GET
    folders = LearningMaterialFolder.objects.order_by('name', 'id').all()

    if role == 'student':
        def _student_group_ids(student: User) -> list[int]:
            ids: list[int] = []
            try:
                if getattr(student, 'group_id', None):
                    ids.append(int(student.group_id))
            except Exception:
                pass
            try:
                extra = list(
                    GroupStudent.objects.filter(student_id=student.id).values_list('group_id', flat=True)
                )
                ids.extend([int(x) for x in extra if x is not None])
            except Exception:
                pass
            return list(dict.fromkeys(ids))

        group_ids = _student_group_ids(request.user)
        access_q = models.Q(materials__is_published=True) & (
            models.Q(materials__group_links__group_id__in=group_ids, materials__group_links__is_published=True)
            | models.Q(materials__group_id__in=group_ids)
            | models.Q(materials__group_links__isnull=True, materials__group_id__isnull=True)
        )
        folders = (
            folders
            .filter(access_q)
            .annotate(materials_count=models.Count('materials', filter=access_q, distinct=True))
            .distinct()
        )

        return Response(
            [
                {
                    'id': f.id,
                    'name': f.name,
                    'materialsCount': int(getattr(f, 'materials_count', 0) or 0),
                    'created_at': f.created_at.isoformat() if getattr(f, 'created_at', None) else '',
                }
                for f in folders
            ]
        )

    # admin/superadmin
    folders = folders.annotate(materials_count=models.Count('materials', distinct=True))
    return Response(
        [
            {
                'id': f.id,
                'name': f.name,
                'materialsCount': int(getattr(f, 'materials_count', 0) or 0),
                'created_at': f.created_at.isoformat() if getattr(f, 'created_at', None) else '',
            }
            for f in folders
        ]
    )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def learning_material_folder_detail(request, pk):
    role = _effective_role(getattr(request, 'user', None))
    if role not in ('admin', 'superadmin', 'student'):
        return Response({'detail': 'Forbidden'}, status=403)

    if request.method in ('PUT', 'DELETE'):
        forbidden = _require_roles(request, ('admin', 'superadmin'))
        if forbidden:
            return forbidden

    try:
        folder = LearningMaterialFolder.objects.get(id=pk)
    except LearningMaterialFolder.DoesNotExist:
        return Response({'success': False, 'error': 'Папку не знайдено'}, status=404)

    if request.method == 'GET':
        if role == 'student':
            def _student_group_ids(student: User) -> list[int]:
                ids: list[int] = []
                try:
                    if getattr(student, 'group_id', None):
                        ids.append(int(student.group_id))
                except Exception:
                    pass
                try:
                    extra = list(
                        GroupStudent.objects.filter(student_id=student.id).values_list('group_id', flat=True)
                    )
                    ids.extend([int(x) for x in extra if x is not None])
                except Exception:
                    pass
                return list(dict.fromkeys(ids))

            group_ids = _student_group_ids(request.user)
            materials_qs = LearningMaterial.objects.filter(folder_id=folder.id, is_published=True)
            if group_ids:
                materials_qs = materials_qs.filter(
                    (
                        models.Q(group_links__group_id__in=group_ids, group_links__is_published=True)
                        | models.Q(group_id__in=group_ids)
                        | models.Q(group_links__isnull=True, group_id__isnull=True)
                    )
                ).distinct()
            else:
                materials_qs = materials_qs.filter(group_links__isnull=True, group_id__isnull=True)

            count = int(materials_qs.count())
            if count <= 0:
                return Response({'success': False, 'error': 'Папку не знайдено'}, status=404)

            return Response(
                {
                    'id': folder.id,
                    'name': folder.name,
                    'materialsCount': count,
                    'created_at': folder.created_at.isoformat() if getattr(folder, 'created_at', None) else '',
                }
            )

        return Response(
            {
                'id': folder.id,
                'name': folder.name,
                'materialsCount': folder.materials.count(),
                'created_at': folder.created_at.isoformat() if getattr(folder, 'created_at', None) else '',
            }
        )

    if request.method == 'PUT':
        name = request.data.get('name', None)
        if name is not None:
            next_name = str(name).strip()
            if not next_name:
                return Response({'success': False, 'error': 'Назва папки обов\'язкова'}, status=400)
            folder.name = next_name
        folder.save()
        return Response({'success': True})

    if request.method == 'DELETE':
        # Detach materials instead of deleting them.
        LearningMaterial.objects.filter(folder=folder).update(folder=None)
        folder.delete()
        return Response({'success': True})


# ===== NOTIFICATIONS =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return Response(
        [
            {
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message or '',
                'is_read': bool(n.is_read),
                'link': n.link or None,
                'created_at': n.created_at.isoformat() if n.created_at else '',
            }
            for n in notifications
        ]
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read(request, pk):
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'success': False, 'error': 'Сповіщення не знайдено'}, status=404)


# ===== USERS =====

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def users_list(request):
    role = _effective_role(getattr(request, 'user', None))
    requested_role = str(request.query_params.get('role', '') or '').strip().lower()

    if request.method == 'POST':
        forbidden = _require_roles(request, ('superadmin',))
        if forbidden:
            return forbidden

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
                if user.role == 'student':
                    GroupStudent.objects.get_or_create(group=group, student=user)
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
    if role in ('admin', 'superadmin'):
        users = User.objects.select_related('group').all()
        if role == 'admin':
            users = users.exclude(is_superadmin=True).exclude(role='superadmin')
        if requested_role:
            users = users.filter(role=requested_role)
    else:
        # Student: allow listing users for private chats (students + admins, minimal fields)
        allowed_roles = {'student', 'admin', 'superadmin', 'user', 'pupil'}
        if requested_role and requested_role not in allowed_roles:
            return Response({'detail': 'Forbidden'}, status=403)

        users = User.objects.filter(
            models.Q(role__iexact='student') |
            models.Q(role__iexact='user') |
            models.Q(role__iexact='pupil') |
            models.Q(role__iexact='admin') |
            models.Q(role__iexact='superadmin')
        ).filter(is_active=True)

        if requested_role:
            users = users.filter(role__iexact=requested_role)

    result = []

    for user in users:
        if role in ('admin', 'superadmin'):
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'phone': user.phone or '',
                'role': _effective_role(user) or user.role,
                'status': getattr(user, 'status', ''),
                'avatar_url': user.avatar_url or '',
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'group': None,
            }
        else:
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': _effective_role(user) or user.role,
                'avatar_url': user.avatar_url or '',
            }

        if role in ('admin', 'superadmin'):
            if user.group:
                user_data['group'] = {
                    'id': user.group.id,
                    'name': user.group.name,
                    'color': user.group.color,
                }

        result.append(user_data)

    return Response(result)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, pk):
    try:
        user = User.objects.select_related('group').get(id=pk)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Користувача не знайдено'}, status=404)

    viewer = request.user
    viewer_role = _effective_role(viewer)
    if viewer_role == 'admin' and (getattr(user, 'is_superadmin', False) or getattr(user, 'role', None) == 'superadmin'):
        return Response({'detail': 'Forbidden'}, status=403)
    if viewer_role == 'student' and user.id != viewer.id:
        return Response({'detail': 'Forbidden'}, status=403)

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
        if viewer_role != 'superadmin':
            return Response({'detail': 'Forbidden'}, status=403)
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
        if viewer_role != 'superadmin':
            return Response({'detail': 'Forbidden'}, status=403)
        user.delete()
        return Response({'success': True})