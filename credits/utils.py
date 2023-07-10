import json
import requests
from bs4 import BeautifulSoup

from django.db import transaction
from django.utils import timezone

from .models import Faculty, Department, Teacher, Direction, Course, Group, EducationYear, Semestr, Subject, DeadLine


class InitData:

    def __init__(self):

        self.facs_file: dict = json.load(open('data/faculties.json', 'r', encoding='utf-8'))
        self.deps_file: dict = json.load(open('data/data.json', 'r', encoding='utf-8'))
        self.groups_file: dict = json.load(open('data/groups.json', 'r', encoding='utf-8'))
    
    def run(self):
        with transaction.atomic():
            self.init_courses()

            self.init_faculties()
            self.init_departments_and_teachers()
            self.init_directs_and_groups()
    
    def init_courses(self):
        for i in range(1, 5):
            course, _ = Course.objects.get_or_create(course=i)

            Semestr.objects.get_or_create(semestr=i*2-1, course=course)
            Semestr.objects.get_or_create(semestr=i*2, course=course)
    
    def init_faculties(self):
        facs = [
            Faculty(name_ru=faculty.get('name_ru'), name_uz=faculty.get('name_uz')) for faculty_id, faculty in self.facs_file.items() if not Faculty.objects.filter(name_ru=faculty.get('name_ru')).exists()
        ]
        if facs: Faculty.objects.bulk_create(facs)
    
    def init_departments_and_teachers(self):
        deps = []
        teachers = []
        teachers_names = []

        for faculty_id, _departments in self.deps_file.items():
            for department, _teachers in _departments.items():
                if not Department.objects.filter(faculty_id=faculty_id, name__icontains=department).exists():
                    department = Department(faculty_id=faculty_id, name=department)
                    deps.append(department)
                else:
                    department = Department.objects.get(faculty_id=faculty_id, name__icontains=department)
                for teacher_name in _teachers:
                    if not Teacher.objects.filter(name__icontains=teacher_name).exists() and teacher_name not in teachers_names:
                        teachers.append(Teacher(name=teacher_name, department=department))
                        teachers_names.append(teacher_name)
                            
        if deps: Department.objects.bulk_create(deps)
        if teachers: Teacher.objects.bulk_create(teachers)
    
    def init_directs_and_groups(self):
        directs = []
        groups = []

        for faculty_name, directions in self.groups_file.items():
            faculty = Faculty.objects.get(name_uz=faculty_name)
            for course, _directions in directions.items():
                course = Course.objects.get(course=int(course))
                
                for direction_name, _groups in _directions.items():

                    if (direction := Direction.objects.filter(name=direction_name, faculty=faculty)).exists():
                        direction = direction.first()
                        direction.course = course
                        direction.save()
                    else:
                        direction = Direction(name=direction_name, course=course, faculty=faculty)
                        directs.append(direction)

                    for group_name, group_data in _groups.items():
                        if not (group := Group.objects.filter(name=group_name, direction=direction, education_form=group_data['education_form'], language=group_data['language'])).exists():
                            group = Group(name=group_name, direction=direction, education_form=group_data['education_form'], language=group_data['language'])
                            groups.append(group)

        Direction.objects.bulk_create(directs)
        Group.objects.bulk_create(groups)
    
def init_deadline():
    for faculty in Faculty.objects.all():
        DeadLine.objects.get_or_create(faculty=faculty)
    
    DeadLine.objects.get_or_create(for_accountant=True)
    DeadLine.objects.get_or_create(for_finances=True)


def parse_deanery_file(file):
    import pandas as pd
    import numpy as np
    
    data = []

    xl_file = pd.read_excel(file, header=None)
    # df = xl_file.where(pd.notnull(xl_file), None)
    df = xl_file.replace({np.nan: None})

    for i, (
        index, hemis_id, name, direction, group, subject, course, lang, education_form,
        year, semestr, edu_hours, hours, lecture, practice, seminar, laboratory, mt, kredit
    ) in df.iterrows():
        try:
            data.append({
                'hemis_id': hemis_id,
                'name': name.strip(),
                'direction': direction.strip(),
                'group': group,
                'subject': subject.strip(),
                'course': int(course),
                'lang': lang.strip(),
                'education_form': education_form.strip(),
                'year': year.strip(),
                'semestr': int(semestr),
                'edu_hours': int(edu_hours),
                'hours': int(hours),
                'lecture': int(lecture) if lecture else None,
                'practice': int(practice) if practice else None,
                'seminar': int(seminar) if seminar else None,
                'laboratory': int(laboratory) if laboratory else None,
                'mt': int(mt) if mt else None,
                'kredit': int(kredit),
            })
        except:
            return None, i
    return data, None


def is_deadline(faculty_id: int = None, for_accountant: bool = None, for_finances: bool = None):
    if not all([faculty_id, for_accountant, for_finances]): return False
    if faculty_id: deadline = DeadLine.objects.get(faculty_id=faculty_id)
    if for_accountant: deadline = DeadLine.objects.get(for_accountant=True)
    if for_finances: deadline = DeadLine.objects.get(for_finances=True)
    return deadline.date < timezone.now()


def get_grade_color(grade: int):
    colors = {
        1: '#000000',
        2: '#FF0000',
        3: '#FFFF00',
        4: '#00FFA8',
        5: '#75FF71'
    }
    return colors[grade]


class StudentLogin:

    hemis_url = 'https://student.samdu.uz'
    login_url = f'{hemis_url}/dashboard/login'
    logout_url = f'{hemis_url}/dashboard/logout'
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def login(self) -> tuple[str, str]:
        try:
            response1 = requests.get(self.login_url, headers=self.headers)

            soup = BeautifulSoup(response1.text, 'html.parser')
            csrf_token = soup.find('input', attrs={'name': '_csrf-frontend'})['value']

            data = {
                'FormStudentLogin[login]': self.username,
                'FormStudentLogin[password]': self.password,
                'FormAdminLogin[rememberMe]': '1',
                '_csrf-frontend': csrf_token
            }

            response = requests.post(self.login_url, headers=self.headers, data=data, cookies=response1.cookies.get_dict())

            soup = BeautifulSoup(response.text, 'html.parser')

            user_name_block = soup.find('img', attrs={'class': 'user-image'})
            if not user_name_block:
                return None, 'login_error'
            user_name = user_name_block['alt']
            
            user_group = soup.find('span', attrs={'class': 'user-role'}).text.strip()

            semestr_block = soup.find('ul', attrs={'class': 'pagination pagination-sm psemester'})
            if not semestr_block:
                return None, 'password_error'
            semestr = semestr_block.find('li', attrs={'class': 'active'}).find('a').text.strip()
            
            
            return user_name, 'success'
        except Exception as e:
            return None, 'error'