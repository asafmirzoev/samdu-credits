import json

from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Q, F
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from users.models import User
from users.choices import UserRoles

from .models import (
    Faculty, Department, Teacher, Course, Direction, Group, EducationYear,
    Semestr, Subject, Student, Credit, DeadLine
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
    return redirect('credits:home')


def get_deanery_overview_page(request: HttpRequest) -> HttpResponse:
    courses = Course.objects.all()
    return render(request, 'credits/src/deanery/overview.html', {'courses': courses})


def get_deanery_search_page(request: HttpRequest) -> HttpResponse:
    name = request.GET.get('name'); page: int = request.GET.get('page', 1)
    credits = Credit.objects.filter(Q(student__name__icontains=name, student__group__direction__faculty=request.user.faculty) | Q(student__hemis_id=name, student__group__direction__faculty=request.user.faculty)) if name else Credit.objects.none()
    paginator = paginated_queryset(credits, page)
    context = {
        'name': name,
        'paginator': paginator
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
    credits = Credit.objects.filter(student__group__direction__course=course, student__group__direction__faculty=request.user.faculty)

    context = {
        'course': course,
        'credits': credits
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
    credits = Credit.objects.filter(student__group__direction=direction)

    context = {
        'course': course,
        'direction': direction,
        'credits': credits
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
    credits = Credit.objects.filter(student__group=group)
    
    context = {
        'course': course,
        'group': group,
        'credits': credits
    }
    return render(request, 'credits/src/deanery/group/group_credits.html', context)


def get_deanery_semestr_page(request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
    group = Group.objects.get(pk=group_id)
    semestr = Semestr.objects.get(pk=semestr_id)
    credits = Credit.objects.filter(student__group=group, semestr=semestr)
    
    context = {
        'group': group,
        'semestr': semestr,
        'credits': credits
    }
    return render(request, 'credits/src/deanery/semestr.html', context)


def deanery_pay_submit(request: HttpRequest, credit_id: int):
    if is_deadline(): return JsonResponse({'success': False})
    
    data: dict = json.loads(request.body.decode('utf-8'))
    _credit_id: int | None = data.get('credit_id')
    if credit_id != int(_credit_id) or not (credits := Credit.objects.filter(pk=credit_id, student__group__direction__faculty=request.user.faculty)).exists(): return JsonResponse({'success': False})
    credits.update(status=CreditStatuses.DEANERY_SETPAID)
    return JsonResponse({'success': True})
    

def get_deanery_upload_page(request: HttpRequest) -> HttpResponse:
    if is_deadline(): return redirect('credits:home')
    return render(request, 'credits/src/deanery/upload.html')


def deanery_upload(request: HttpRequest) -> HttpResponse:
    if is_deadline(): return redirect('credits:home')

    user: User = request.user; files: dict = request.FILES

    items = parse_deanery_file(files.get('file'))
    if not items: return redirect('upload')

    with transaction.atomic():
        for i, item in enumerate(items):
            course = Course.objects.get(course=item['course'])
            semestr = Semestr.objects.get(semestr=item['semestr'])

            print(item['hemis_id'])
            direction = Direction.objects.get(name=item['direction'], faculty=user.faculty)
            group = Group.objects.get(name=item['group'], direction=direction)
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
                credit.amount = float((direction.kontraktamount.amount / credit.edu_hours) * credit.subject.credits, 2)
                credit.save()

    return redirect('credits:home')


def get_accountant_overview_page(request: HttpRequest):
    faculties = Faculty.objects.all()
    return render(request, 'credits/src/accountant/overview.html', {'faculties': faculties})


def get_accountant_search_page(request: HttpRequest):
    name = request.GET.get('name'); page: int = request.GET.get('page', 1)
    credits = Credit.objects.filter(Q(student__name__icontains=name) | Q(student__hemis_id=name)) if name else Credit.objects.none()
    paginator = paginated_queryset(credits, page)
    context = {
        'name': name,
        'paginator': paginator
    }
    return render(request, 'credits/src/accountant/search.html', context=context)


def get_accountant_faculty_page(request: HttpRequest, faculty_id: int):
    faculty = Faculty.objects.get(pk=faculty_id)
    courses = Course.objects.all()
    return render(request, 'credits/src/accountant/faculty.html', {'faculty': faculty, 'courses': courses})


def get_accountant_faculty_credits_page(request: HttpRequest, faculty_id: int) -> HttpResponse:
    page = request.GET.get('page', 1)

    faculty = Faculty.objects.get(pk=faculty_id)
    credits = Credit.objects.filter(student__group__direction__faculty=faculty)

    paginator = paginated_queryset(credits, page)
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
    credits = Credit.objects.filter(student__group__direction__course=course, student__group__direction__faculty=faculty)

    paginator = paginated_queryset(credits, page)
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
    credits = Credit.objects.filter(student__group=group, semestr=semestr)
    
    context = {
        'group': group,
        'semestr': semestr,
        'credits': credits
    }
    return render(request, 'credits/src/accountant/semestr.html', context)


def accountant_pay_submit(request: HttpRequest, credit_id: int):
    if is_deadline(): return JsonResponse({'success': False})

    data: dict = json.loads(request.body.decode('utf-8'))
    _credit_id: int | None = data.get('credit_id')
    if credit_id != int(_credit_id) or not (credits := Credit.objects.filter(pk=credit_id)).exists(): return JsonResponse({'success': False})
    credits.update(status=CreditStatuses.ACCOUNTANT_SUBMITED)
    return JsonResponse({'success': True})


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

        credits = Credit.objects.filter(student__group__direction=direction)

        credits_for_update = []
        for credit in credits:
            credit.status = CreditStatuses.FINANCE_SETTED
            credit.amount = round((direction.kontraktamount.amount / credit.edu_hours) * credit.subject.credits, 2)
            credits_for_update.append(credit)
        Credit.objects.bulk_update(credits_for_update, ['status', 'amount'])

    return redirect('credits:finances-course', faculty_id=direction.faculty.pk, course_id=course_id)


def get_edupart_overview_page(request: HttpRequest):
    faculties = Faculty.objects.all()
    return render(request, 'credits/src/edupart/overview.html', {'faculties': faculties})


def get_edupart_search_page(request: HttpRequest):
    name = request.GET.get('name'); page: int = request.GET.get('page', 1)
    credits = Credit.objects.filter(Q(student__name__icontains=name) | Q(student__hemis_id=name)) if name else Credit.objects.none()
    paginator = paginated_queryset(credits, page)
    context = {
        'name': name,
        'paginator': paginator
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
    return render(request, 'credits/src/accountant/faculty/faculty_credits.html', context)


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