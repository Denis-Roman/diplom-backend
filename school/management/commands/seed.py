import bcrypt
from django.core.management.base import BaseCommand
from school.models import (
    User, Group, GroupStudent, Subject, Lesson, Task,
    TaskSubmission, Invoice, ExtraNews, StudentPoint, Team, TeamMember,
)


def hash_pw(raw):
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # ── Admin user ──
        admin, _ = User.objects.update_or_create(
            email='admin@logo.school',
            defaults={
                'password': hash_pw('admin123'),
                'name': 'Адміністратор',
                'role': 'admin',
                'status': 'active',
            }
        )
        self.stdout.write(f'  Admin: {admin.email}')

        # ── Subjects ──
        subjects_data = [
            ('Adobe Illustrator', 'Ai', '#FF9A00'),
            ('Adobe Photoshop', 'Ps', '#31A8FF'),
            ('Figma', 'Fg', '#A259FF'),
            ('After Effects', 'Ae', '#9999FF'),
            ('Основи дизайну', 'Дз', '#059669'),
        ]
        subjects = {}
        for name, short, color in subjects_data:
            s, _ = Subject.objects.update_or_create(
                short_name=short,
                defaults={'name': name, 'color': color},
            )
            subjects[short] = s
        self.stdout.write(f'  Subjects: {len(subjects)}')

        # ── Groups ──
        groups_data = [
            ('Illustrator - Група 1', '#FF9A00'),
            ('Photoshop - Група 1', '#31A8FF'),
            ('After Effects - Група 1', '#9999FF'),
            ('Design Pro 2024', '#7c3aed'),
        ]
        groups = {}
        for name, color in groups_data:
            g, _ = Group.objects.update_or_create(
                name=name,
                defaults={'color': color, 'description': f'Навчальна група {name}'},
            )
            groups[name] = g
        self.stdout.write(f'  Groups: {len(groups)}')

        # ── Students ──
        students_data = [
            ('Олена Ковальчук', 'o.kovalchuk@student.logo.com', 'Illustrator - Група 1'),
            ('Дмитро Бондар', 'd.bondar@student.logo.com', 'Illustrator - Група 1'),
            ('Марія Шевченко', 'm.shevchenko@student.logo.com', 'Illustrator - Група 1'),
            ('Олександр Петренко', 'o.petrenko@student.logo.com', 'Illustrator - Група 1'),
            ('Марія Коваленко', 'm.kovalenko@student.logo.com', 'Illustrator - Група 1'),
            ('Іван Шевченко', 'i.shevchenko@student.logo.com', 'Illustrator - Група 1'),
            ('Андрій Петренко', 'a.petrenko@student.logo.com', 'Photoshop - Група 1'),
            ('Юлія Мельник', 'y.melnyk@student.logo.com', 'Photoshop - Група 1'),
            ('Дмитро Бондаренко', 'd.bondarenko@student.logo.com', 'Photoshop - Група 1'),
            ('Софія Мельник', 's.melnyk@student.logo.com', 'After Effects - Група 1'),
            ('Катерина Лисенко', 'k.lysenko@student.logo.com', 'After Effects - Група 1'),
            ('Максим Ткаченко', 'm.tkachenko@student.logo.com', 'Photoshop - Група 1'),
        ]
        students = {}
        for name, email, group_name in students_data:
            u, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    'password': hash_pw('student123'),
                    'name': name,
                    'role': 'student',
                    'status': 'active',
                }
            )
            if group_name in groups:
                GroupStudent.objects.get_or_create(group=groups[group_name], student=u)
            students[email] = u
        self.stdout.write(f'  Students: {len(students)}')

        # ── Lessons ──
        lessons_data = [
            ('Основи векторної графіки', 'Ai', 'Illustrator - Група 1', '2026-02-04', '10:00', '11:30'),
            ('Ретуш та корекція кольору', 'Ps', 'Photoshop - Група 1', '2026-02-04', '14:00', '15:30'),
            ('Анімація тексту', 'Ae', 'After Effects - Група 1', '2026-02-05', '10:00', '11:30'),
            ('Робота з шарами', 'Ps', 'Photoshop - Група 1', '2026-02-06', '10:00', '11:30'),
            ('Кольорова схема бренду', 'Дз', 'Design Pro 2024', '2026-02-07', '12:00', '13:30'),
        ]
        for title, sub_short, g_name, dt, st, et in lessons_data:
            Lesson.objects.get_or_create(
                title=title,
                scheduled_date=dt,
                defaults={
                    'subject': subjects.get(sub_short),
                    'group': groups.get(g_name),
                    'start_time': st,
                    'end_time': et,
                    'status': 'scheduled',
                }
            )
        self.stdout.write(f'  Lessons: {Lesson.objects.count()}')

        # ── Tasks ──
        tasks_data = [
            ('Створення логотипу', 'homework', 'Ai', 'Illustrator - Група 1', 100, '2026-02-15'),
            ('Класна робота: Вектор', 'classwork', 'Ai', 'Illustrator - Група 1', 20, '2026-02-10'),
            ('Контрольна #1', 'test', 'Ai', 'Illustrator - Група 1', 100, '2026-02-20'),
            ('Ретуш фотографії', 'homework', 'Ps', 'Photoshop - Група 1', 50, '2026-02-12'),
            ('Колаж з фотографій', 'homework', 'Ps', 'Photoshop - Група 1', 60, '2026-02-22'),
            ('Іконки для додатку', 'homework', 'Ai', 'Illustrator - Група 1', 80, '2026-02-20'),
            ('Банер', 'homework', 'Ai', 'Illustrator - Група 1', 50, '2026-02-25'),
            ('Маски', 'homework', 'Ps', 'Photoshop - Група 1', 30, '2026-02-18'),
            ('Кольорокорекція', 'practice', 'Ps', 'Photoshop - Група 1', 20, '2026-02-28'),
            ('Анімація тексту', 'homework', 'Ae', 'After Effects - Група 1', 50, '2026-02-18'),
            ('Motion Graphics', 'homework', 'Ae', 'After Effects - Група 1', 50, '2026-02-22'),
            ('Композитинг', 'project', 'Ae', 'After Effects - Група 1', 50, '2026-02-26'),
            ('Фінальний проект', 'project', 'Ae', 'After Effects - Група 1', 50, '2026-03-01'),
        ]
        tasks = {}
        for title, ttype, sub_short, g_name, max_g, due in tasks_data:
            t, _ = Task.objects.get_or_create(
                title=title,
                group=groups.get(g_name),
                defaults={
                    'type': ttype,
                    'subject': subjects.get(sub_short),
                    'max_grade': max_g,
                    'due_date': due,
                }
            )
            tasks[title] = t
        self.stdout.write(f'  Tasks: {len(tasks)}')

        # ── Submissions & grades ──
        submissions = [
            ('o.kovalchuk@student.logo.com', 'Створення логотипу', 'graded', 95),
            ('o.kovalchuk@student.logo.com', 'Класна робота: Вектор', 'graded', 18),
            ('d.bondar@student.logo.com', 'Створення логотипу', 'graded', 88),
            ('d.bondar@student.logo.com', 'Класна робота: Вектор', 'graded', 20),
            ('m.shevchenko@student.logo.com', 'Створення логотипу', 'graded', 72),
            ('m.shevchenko@student.logo.com', 'Класна робота: Вектор', 'graded', 15),
            ('a.petrenko@student.logo.com', 'Ретуш фотографії', 'graded', 45),
            ('s.melnyk@student.logo.com', 'Анімація тексту', 'graded', 48),
            ('s.melnyk@student.logo.com', 'Motion Graphics', 'graded', 42),
            ('s.melnyk@student.logo.com', 'Композитинг', 'graded', 35),
            ('s.melnyk@student.logo.com', 'Фінальний проект', 'graded', 35),
            ('m.kovalenko@student.logo.com', 'Створення логотипу', 'graded', 92),
            ('i.shevchenko@student.logo.com', 'Створення логотипу', 'pending', None),
            ('m.tkachenko@student.logo.com', 'Ретуш фотографії', 'graded', 45),
        ]
        for email, task_title, sub_status, grade in submissions:
            student = students.get(email)
            task = tasks.get(task_title)
            if not student or not task:
                continue
            sub_obj, _ = TaskSubmission.objects.update_or_create(
                task=task, student=student,
                defaults={
                    'status': sub_status,
                    'grade': grade,
                    'comment': 'Моя робота',
                }
            )
            if grade and grade > 0:
                StudentPoint.objects.update_or_create(
                    student=student, source_type='task', source_id=task.id,
                    defaults={'points': grade},
                )
        self.stdout.write(f'  Submissions: {TaskSubmission.objects.count()}')

        # ── Invoices ──
        inv_data = [
            ('m.kovalenko@student.logo.com', 12000, 8000, 3, 2, 'partial', 'Курс Illustrator - 3 місяці'),
            ('a.petrenko@student.logo.com', 9000, 9000, 1, 1, 'paid', 'Курс Photoshop - повна оплата'),
            ('s.melnyk@student.logo.com', 15000, 0, 5, 1, 'pending', 'Курс After Effects - 5 місяців'),
        ]
        for email, amount, paid, inst, cur, inv_status, desc in inv_data:
            student = students.get(email)
            if not student:
                continue
            Invoice.objects.get_or_create(
                student=student,
                description=desc,
                defaults={
                    'amount': amount,
                    'paid_amount': paid,
                    'installments': inst,
                    'current_installment': cur,
                    'status': inv_status,
                    'due_date': '2026-02-15',
                }
            )
        self.stdout.write(f'  Invoices: {Invoice.objects.count()}')

        # ── Extra news ──
        ExtraNews.objects.get_or_create(
            title='Відкрито набір на весняний курс',
            defaults={
                'description': 'Запис на нові групи з дизайну',
                'media_type': 'image',
                'is_active': True,
            }
        )

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write(f'  Login as admin: admin@logo.school / admin123')
        self.stdout.write(f'  Login as student: o.kovalchuk@student.logo.com / student123')
