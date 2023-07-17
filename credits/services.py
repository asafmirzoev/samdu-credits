import json
from urllib.parse import quote, unquote

from django.http import HttpRequest, HttpResponse, JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, F
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from users.models import User
from users.choices import UserRoles

from .models import (
    Faculty, Department, Teacher, Course, Direction, Group, EducationYear,
    Semestr, Subject, Student, Credit, PaySet, DeadLine
)
from .choices import CreditStatuses
from .paginator import paginated_queryset
from .utils import parse_deanery_file, is_deadline, StudentLogin


def get_home_page(request: HttpRequest) -> HttpResponse:
    user: User = request.user
    if not user.is_authenticated: return redirect('users:login')
    if user.role == UserRoles.DEKAN: return redirect('credits:deanery-overview')
    if user.role == UserRoles.FINANCE: return redirect('credits:finances-overview')
    if user.role == UserRoles.ACCOUNTANT: return redirect('credits:accountant-overview')
    if user.role == UserRoles.EDUPART: return redirect('credits:edu-part-overview')
    raise Http404()
    

def get_student_credits_page(request: HttpRequest) -> HttpResponse:
    return render(request, 'credits/students/login.html')


def student_credits(request: HttpRequest) -> HttpResponse:
    data = request.POST
    # login = StudentLogin(username=data.get('username'), password=data.get('password'))
    # name, error = login.login()
    student = students.first() if (students := Student.objects.filter(hemis_id=data.get('username'))).exists() else None
    if student:
        credits = Credit.objects.filter(student=student)
        return render(request, 'credits/students/credits.html', {'credits': credits, 'student': student})
    messages.error(request, _('Неверный логин или для этого ID нет информации'))
    return redirect('credits:student-credits')


def get_invoice(payset_id: int):
    return FileResponse(PaySet.objects.get(pk=payset_id).invoice)


def get_deanery_overview_page(request: HttpRequest) -> HttpResponse:
    courses = Course.objects.all()
    return render(request, 'credits/src/deanery/overview.html', {'courses': courses})


def get_deanery_search_page(request: HttpRequest) -> HttpResponse:
    name = request.GET.get('name'); page: int = request.GET.get('page', 1)
    students = Student.objects.filter(Q(name__icontains=name, group__direction__faculty=request.user.faculty) | Q(hemis_id=name, group__direction__faculty=request.user.faculty)) if name else Student.objects.none()
    paginator = paginated_queryset(students, page)

    redirect_url = quote(f"{reverse('credits:deanery-search')}?name={name}&page={page}")

    context = {
        'name': name,
        'paginator': paginator,
        'redirect_url': redirect_url
    }
    
    return render(request, 'credits/src/deanery/search.html', context=context)


def get_deanery_course_page(request: HttpRequest, course_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    directions = course.direction_set.filter(faculty=request.user.faculty)

    context = {
        'course': course,
        'directions': directions
    }
    return render(request, 'credits/src/deanery/course.html', context)


def get_deanery_course_credits_page(request: HttpRequest, course_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    students = Student.objects.filter(group__direction__course=course, group__direction__faculty=request.user.faculty)

    context = {
        'course': course,
        'students': students
    }
    return render(request, 'credits/src/deanery/course/course_credits.html', context)


def get_deanery_direction_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    direction = Direction.objects.get(pk=direction_id)
    context = {
        'course': course,
        'direction': direction,
    }
    return render(request, 'credits/src/deanery/direction.html', context)


def get_deanery_direction_credits_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    direction = Direction.objects.get(pk=direction_id)
    students = Student.objects.filter(group__direction=direction)

    context = {
        'course': course,
        'direction': direction,
        'students': students
    }
    return render(request, 'credits/src/deanery/direction/direction_credits.html', context)


def get_deanery_group_page(request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    group = Group.objects.get(pk=group_id)
    semestrs = Semestr.objects.all()
    context = {
        'course': course,
        'group': group,
        'semestrs': semestrs
    }
    return render(request, 'credits/src/deanery/group.html', context)


def get_deanery_group_credits_page(request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    group = Group.objects.get(pk=group_id)
    students = Student.objects.filter(group=group)
    
    context = {
        'course': course,
        'group': group,
        'students': students
    }
    return render(request, 'credits/src/deanery/group/group_credits.html', context)


def get_deanery_semestr_page(request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
    group = Group.objects.get(pk=group_id)
    semestr = Semestr.objects.get(pk=semestr_id)
    students = {student: credits for student in Student.objects.filter(group=group) if (credits := student.credit_set.filter(semestr=semestr)).exists()}

    redirect_url = reverse('credits:deanery-semestr', kwargs={'group_id': group_id, 'semestr_id': semestr_id})
    
    context = {
        'group': group,
        'semestr': semestr,
        'students': students,
        'redirect_url': redirect_url
    }
    return render(request, 'credits/src/deanery/semestr.html', context)


def deanery_pay_submit(request: HttpRequest, student_id: int):
    redirect_url = request.GET.get('redirect_url', '/')
    if is_deadline(): return redirect(redirect_url)
    
    data: dict = request.POST
    if not (students := Student.objects.filter(pk=student_id, group__direction__faculty=request.user.faculty)).exists():
        messages.error(request, _('Такого студента не существует'))
        return redirect(redirect_url)
    
    file = request.FILES.get(f'pay-incoice{student_id}')

    if not file:
        messages.error(request, _('Файл квитанции обязателен'))
        return redirect(redirect_url)

    if file.size > 1_048_576:
        messages.error(request, _('Размер файла не может превышать 1MB'))
        return redirect(redirect_url)
    
    with transaction.atomic():
        credits = [i.replace(f'payed-{student_id}-', '') for i in data.keys() if f'payed-{student_id}-' in i]
        (credits := Credit.objects.filter(pk__in=credits)).update(status=CreditStatuses.DEANERY_SETPAID)

        pay_set = PaySet.objects.create(student=students.first(), pay_time=data.get(f'pay-date{student_id}'), invoice=file)
        pay_set.credits.set(credits)

    return redirect(redirect_url)
    

def get_deanery_upload_page(request: HttpRequest) -> HttpResponse:
    if is_deadline(): return redirect('credits:home')
    return render(request, 'credits/src/deanery/upload.html')


def deanery_upload(request: HttpRequest) -> HttpResponse:
    if is_deadline(): return redirect('credits:home')

    user: User = request.user; files: dict = request.FILES

    items, line = parse_deanery_file(files.get('file'))
    if not items:
        messages.error(request, f'Xato {line + 1} qatorda')
        return redirect('credits:deanery-upload')

    with transaction.atomic():
        for i, item in enumerate(items):
            
            course = Course.objects.get(course=item['course'])
            semestr = Semestr.objects.get(semestr=item['semestr'])

            if not (directions := Direction.objects.filter(name=item['direction'], faculty=user.faculty)).exists():
                transaction.set_rollback(True)
                messages.error(request, f"Yo'nalishda xato (topilmadi). Qator: {i + 1}")
                return redirect('credits:deanery-upload')
            
            direction = directions.first()

            if not (groups := Group.objects.filter(name=item['group'], direction=direction)).exists():
                transaction.set_rollback(True)
                messages.error(request, f'Guruhda xato (topilmadi). Qator: {i + 1}')
                return redirect('credits:deanery-upload')
            
            group = groups.first()

            if (students := Student.objects.filter(hemis_id=item['hemis_id'])).exists() and not students.filter(name=item['name'].upper(), group=group):
                transaction.set_rollback(True)
                messages.error(request, f"Student ma'lumitida xato. Qator: {i + 1}")
                return redirect('credits:deanery-upload')
            
            student, _ = Student.objects.get_or_create(group=group, name=item['name'].upper(), hemis_id=item['hemis_id'])

            edu_year, _ = EducationYear.objects.get_or_create(year=item['year'])
            
            subject, _ = Subject.objects.get_or_create(
                name=item['subject'],
                hours=item['hours'],
                lecture_hours=item['lecture'],
                practice_hours=item['practice'],
                seminar_hours=item['seminar'],
                laboratory_hours=item['laboratory'],
                independent_hours=item['mt'],
                credits=item['kredit']
            )

            credit, _ = Credit.objects.get_or_create(
                student=student,
                subject=subject,
                semestr=semestr,
                edu_year=edu_year,
                edu_hours=item['edu_hours']
            )

            if hasattr(direction, 'kontraktamount') and direction.kontraktamount.amount:
                credit.status = CreditStatuses.FINANCE_SETTED
                credit.amount = round((direction.kontraktamount.amount / credit.edu_hours) * credit.subject.credits, 2)
                credit.save()

    return redirect('credits:home')


def get_accountant_overview_page(request: HttpRequest):
    faculties = Faculty.objects.all()
    return render(request, 'credits/src/accountant/overview.html', {'faculties': faculties})


def get_accountant_search_page(request: HttpRequest):
    name = request.GET.get('name'); page: int = request.GET.get('page', 1)
    students = Student.objects.filter(Q(name__icontains=name) | Q(hemis_id=name)) if name else Student.objects.none()
    paginator = paginated_queryset(students, page)

    redirect_url = quote(f"{reverse('credits:accountant-search')}?name={name}&page={page}")

    context = {
        'name': name,
        'paginator': paginator,
        'redirect_url': redirect_url
    }
    return render(request, 'credits/src/accountant/search.html', context=context)


def get_accountant_faculty_page(request: HttpRequest, faculty_id: int):
    faculty = Faculty.objects.get(pk=faculty_id)
    courses = Course.objects.all()
    return render(request, 'credits/src/accountant/faculty.html', {'faculty': faculty, 'courses': courses})


def get_accountant_faculty_credits_page(request: HttpRequest, faculty_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    faculty = Faculty.objects.get(pk=faculty_id)
    students = Student.objects.filter(group__direction__faculty=faculty)

    paginator = paginated_queryset(students, page)
    context = {
        'faculty': faculty,
        'paginator': paginator
    }
    return render(request, 'credits/src/accountant/faculty/faculty_credits.html', context)


def get_accountant_course_page(request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
    faculty = Faculty.objects.get(pk=faculty_id)
    course = Course.objects.get(pk=course_id)
    directions = course.direction_set.filter(faculty=faculty)
    context = {
        'faculty': faculty,
        'course': course,
        'directions': directions
    }
    return render(request, 'credits/src/accountant/course.html', context)


def get_accountant_course_credits_page(request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    faculty = Faculty.objects.get(pk=faculty_id)
    course = Course.objects.get(pk=course_id)
    students = Student.objects.filter(group__direction__course=course, group__direction__faculty=faculty)

    paginator = paginated_queryset(students, page)
    context = {
        'faculty': faculty,
        'course': course,
        'paginator': paginator
    }
    return render(request, 'credits/src/accountant/course/course_credits.html', context)


def get_accountant_direction_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    direction = Direction.objects.get(pk=direction_id)
    context = {
        'course': course,
        'direction': direction,
    }
    return render(request, 'credits/src/accountant/direction.html', context)


def get_accountant_group_page(request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    group = Group.objects.get(pk=group_id)
    semestrs = Semestr.objects.all()
    context = {
        'course': course,
        'group': group,
        'semestrs': semestrs
    }
    return render(request, 'credits/src/accountant/group.html', context)


def get_accountant_semestr_page(request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
    group = Group.objects.get(pk=group_id)
    semestr = Semestr.objects.get(pk=semestr_id)
    students = {student: credits for student in Student.objects.filter(group=group) if (credits := student.credit_set.filter(semestr=semestr))}
    
    context = {
        'group': group,
        'semestr': semestr,
        'students': students
    }
    return render(request, 'credits/src/accountant/semestr.html', context)


def accountant_pay_submit(request: HttpRequest, payset_id: int):
    redirect_url = request.GET.get('redirect_url', '/')
    if is_deadline(): return redirect(redirect_url)

    if not (paysets := PaySet.objects.filter(pk=payset_id)).exists():
        messages.error(request, _('Оплата не найдена'))
        return redirect(redirect_url)
    
    with transaction.atomic():

        paysets.update(submited=True)
        for credit in paysets.first().credits.all():
            credit.status = CreditStatuses.ACCOUNTANT_SUBMITED
            credit.save()
        
    return redirect(redirect_url)


def get_finances_overview_page(request: HttpRequest):
    faculties = Faculty.objects.all()
    return render(request, 'credits/src/finances/overview.html', {'faculties': faculties})


def get_finances_faculty_page(request: HttpRequest, faculty_id: int):
    faculty = Faculty.objects.get(pk=faculty_id)
    courses = Course.objects.all()
    return render(request, 'credits/src/finances/faculty.html', {'faculty': faculty, 'courses': courses})


def get_finances_course_page(request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
    faculty = Faculty.objects.get(pk=faculty_id)
    course = Course.objects.get(pk=course_id)
    directions = course.direction_set.filter(faculty=faculty)
    context = {
        'faculty': faculty,
        'course': course,
        'directions': directions
    }
    return render(request, 'credits/src/finances/course.html', context)


def get_finances_direction_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    if is_deadline(): return JsonResponse({'success': False})

    with transaction.atomic():
        direction = Direction.objects.get(pk=direction_id)
        direction.kontraktamount.amount = float(request.POST.get('amount'))
        direction.kontraktamount.save()

        credits = Credit.objects.filter(student__group__direction=direction, status__in=[CreditStatuses.DEANERY_UPLOADED, CreditStatuses.FINANCE_SETTED])

        credits_for_update = []
        for credit in credits:
            credit.status = CreditStatuses.FINANCE_SETTED
            credit.amount = round((direction.kontraktamount.amount / credit.edu_hours) * credit.subject.credits, 2)
            credits_for_update.append(credit)
        Credit.objects.bulk_update(credits_for_update, ['status', 'amount'])

    return redirect('credits:finances-course', faculty_id=direction.faculty.pk, course_id=course_id)


def get_finances_credits_page(request: HttpRequest, direction_id: int):
    page = request.GET.get('page', 1)

    students = Student.objects.filter(group__direction_id=direction_id)
    
    paginator = paginated_queryset(students, page)
    context = {
        'paginator': paginator
    }
    return render(request, 'credits/src/finances/credits.html', context)



def get_edupart_overview_page(request: HttpRequest):
    faculties = Faculty.objects.all()
    return render(request, 'credits/src/edupart/overview.html', {'faculties': faculties})


def get_edupart_search_page(request: HttpRequest):
    name = request.GET.get('name', ''); page: int = request.GET.get('page', 1)
    faculty_id: int = request.GET.get('faculty_id'); course_id: int = request.GET.get('course_id'); direction_id: int = request.GET.get('direction_id'); group_id: int = request.GET.get('group_id');

    credits = Credit.objects.all()

    if name: credits = credits.filter(Q(student__name__icontains=name) | Q(student__hemis_id=name))

    faculties = Faculty.objects.all(); courses = None; directions = None; groups = None

    if faculty_id:
        credits = credits.filter(student__group__direction__faculty_id=faculty_id)
        courses = Course.objects.all()
    
    if course_id:
        credits = credits.filter(student__group__direction__faculty_id=faculty_id, student__group__direction__course_id=course_id)
        directions = Direction.objects.filter(faculty_id=faculty_id, course_id=course_id)
    
    if direction_id:
        credits = credits.filter(student__group__direction_id=direction_id)
        groups = Group.objects.filter(direction_id=direction_id)
    
    if group_id:
        credits = credits.filter(student__group_id=group_id)

    paginator = paginated_queryset(credits, page)
    context = {
        'name': name,
        'paginator': paginator,

        'faculty_id': int(faculty_id) if faculty_id else '',
        'course_id': int(course_id) if course_id else '',
        'direction_id': int(direction_id) if direction_id else '',
        'group_id': int(group_id) if group_id else '',

        'faculties': faculties,
        'courses': courses,
        'directions': directions,
        'groups': groups
    }
    return render(request, 'credits/src/edupart/search.html', context=context)


def get_edupart_faculty_page(request: HttpRequest, faculty_id: int):
    faculty = Faculty.objects.get(pk=faculty_id)
    courses = Course.objects.all()
    return render(request, 'credits/src/edupart/faculty.html', {'faculty': faculty, 'courses': courses})


def get_edupart_faculty_credits_page(request: HttpRequest, faculty_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    faculty = Faculty.objects.get(pk=faculty_id)
    credits = Credit.objects.filter(student__group__direction__faculty=faculty)

    paginator = paginated_queryset(credits, page)
    context = {
        'faculty': faculty,
        'paginator': paginator
    }
    return render(request, 'credits/src/edupart/faculty/faculty_credits.html', context)


def get_edupart_course_page(request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
    faculty = Faculty.objects.get(pk=faculty_id)
    course = Course.objects.get(pk=course_id)
    directions = course.direction_set.filter(faculty=faculty)
    context = {
        'faculty': faculty,
        'course': course,
        'directions': directions
    }
    return render(request, 'credits/src/edupart/course.html', context)


def get_edupart_course_credits_page(request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    faculty = Faculty.objects.get(pk=faculty_id)
    course = Course.objects.get(pk=course_id)
    credits = Credit.objects.filter(student__group__direction__course=course, student__group__direction__faculty=faculty)

    paginator = paginated_queryset(credits, page)
    context = {
        'faculty': faculty,
        'course': course,
        'paginator': paginator
    }
    return render(request, 'credits/src/edupart/course/course_credits.html', context)


def get_edupart_direction_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    direction = Direction.objects.get(pk=direction_id)
    context = {
        'course': course,
        'direction': direction,
    }
    return render(request, 'credits/src/edupart/direction.html', context)


def get_edupart_direction_cerdits_page(request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    direction = Direction.objects.get(pk=direction_id)
    course = Course.objects.get(pk=course_id)
    credits = Credit.objects.filter(student__group__direction__course=course, student__group__direction=direction)

    paginator = paginated_queryset(credits, page)
    context = {
        'direction': direction,
        'course': course,
        'paginator': paginator
    }
    return render(request, 'credits/src/edupart/direction/direction_credits.html', context)


def get_edupart_group_page(request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
    course = Course.objects.get(pk=course_id)
    group = Group.objects.get(pk=group_id)
    semestrs = Semestr.objects.all()
    context = {
        'course': course,
        'group': group,
        'semestrs': semestrs
    }
    return render(request, 'credits/src/edupart/group.html', context)


def get_edupart_group_credits_page(request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    group = Group.objects.get(pk=group_id)
    course = Course.objects.get(pk=course_id)
    credits = Credit.objects.filter(student__group__direction__course=course, student__group=group)

    paginator = paginated_queryset(credits, page)
    context = {
        'group': group,
        'course': course,
        'paginator': paginator
    }
    return render(request, 'credits/src/edupart/group/group_credits.html', context)


def get_edupart_semestr_page(request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
    group = Group.objects.get(pk=group_id)
    semestr = Semestr.objects.get(pk=semestr_id)
    credits = Credit.objects.filter(student__group=group, semestr=semestr)
    
    context = {
        'group': group,
        'semestr': semestr,
        'credits': credits
    }
    return render(request, 'credits/src/edupart/semestr.html', context)


def get_edupart_deadline_page(request: HttpRequest) -> HttpResponse:
    deadlines = DeadLine.objects.all()
    return render(request, 'credits/src/edupart/deadline.html', {'deadlines': deadlines})


def set_edupart_deadline_page(request: HttpRequest, deadline_id: int) -> HttpResponse:
    DeadLine.objects.filter(pk=deadline_id).update(date=request.POST.get(f'date-{deadline_id}'))
    return redirect('credits:edu-part-deadline')