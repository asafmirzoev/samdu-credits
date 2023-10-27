from uuid import uuid4
import json
import requests
import time
import pickle
import logging
from bs4 import BeautifulSoup

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.conf import settings

from .models import (
    Faculty, Direction, Course, Group, EducationYear, Semestr, Subject, DeadLine, Credit,
    DirectionEduYear, Student
)


logging.basicConfig(filename='logs.log', level=logging.INFO)

    
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


def credits_to_excel(credits: QuerySet[Credit]):
    import pandas as pd

    data = [
        [
            i + 1,
            credit.student.hemis_id,
            credit.student.name,
            credit.student.group.direction.name,
            credit.student.group.name,
            credit.subject.name,
            credit.semestr.course.course,
            credit.student.group.language,
            credit.student.group.education_form,
            credit.edu_year.year,
            credit.semestr.semestr,
            credit.subject.hours,
            credit.subject.lecture_hours,
            credit.subject.practice_hours,
            credit.subject.seminar_hours,
            credit.subject.laboratory_hours,
            credit.subject.independent_hours,
            credit.subject.credits,
            credit.student.group.direction.kontraktamount.amount if hasattr(credit.student.group.direction, 'kontraktamount') else '',
            credit.amount,
            credit.get_status_display()
        ] for i, credit in enumerate(credits)
    ]
    df = pd.DataFrame(data)

    filename = settings.BASE_DIR / f'files/credits/credits-{uuid4()}.xlsx'
    df.to_excel(filename, header=False, index=False)
    return filename

def is_deadline(faculty_id: int = None, for_accountant: bool = None, for_finances: bool = None):
    if not any([faculty_id, for_accountant, for_finances]): return False
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


class ParseBase:

    def __init__(self):

        with open(settings.BASE_DIR / 'data/samdu.pkl', 'rb') as f:
            self.session: requests.Session = pickle.load(f)

        self.headers_for_ajax = {
            'authority': 'hemis.samdu.uz',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,uz;q=0.6',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://hemis.samdu.uz',
            'pragma': 'no-cache',
            'referer': 'https://hemis.samdu.uz/performance/debtors',
            'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'x-csrf-token': '9m0UZwX6VQMmPM-aW8Tc3yyjpRgXVVYu91qQRr-B_emkWHUSMMwWZmxlvfUi9I28TcvTSXM2JVabGPd288qMuQ==',
            'x-requested-with': 'XMLHttpRequest',
        }
                

class ParseCreditors(ParseBase):

    def __init__(self):
        self.base_url = 'https://hemis.samdu.uz/performance/debtors'
        super().__init__()
    
    def parse(self):
        start = timezone.now()

        # self.faculties()
        # self.directions()
        # self.years()
        # self.groups()
        # ParseCurriculum().parse()
        # ParseStudents().parse()
        self.creditors()

        self.session.get(f'https://api.telegram.org/bot6292467753:AAEN0gGT5TEM4BNQA6JZE2hfYZukPPVBuwA/sendMessage?chat_id=1251050357&text={start - timezone.now()}')

    def faculties(self):

        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        current_year = soup.find('select', attrs={'id': '_education_year_search'}).find('option', selected=True).get('value')

        for option in reversed(soup.find('select', attrs={'id': '_education_year_search'}).find_all('option')):
            if not (opt_value := option.get('value')): continue
            EducationYear.objects.get_or_create(year_id=opt_value, defaults={'year': option.getText(strip=True), 'current': opt_value == current_year})
            if opt_value == current_year: break

        options = soup.find('select', attrs={'id': 'filterform-_faculty'}).find_all('option')
        Faculty.objects.bulk_create([Faculty(faculty_id=opt_value, name=option.getText().strip()) for option in options if (opt_value := option.get('value')) and not Faculty.objects.filter(faculty_id=opt_value).exists()])

    def directions(self) -> list[dict]:

        _directions = []
        for faculty in Faculty.objects.all():

            params = {
                'FilterForm[_faculty]': faculty.faculty_id,
                'FilterForm[_curriculum]': '',
                '_pjax': '#admin-grid',
            }

            response = self.session.get(self.base_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')

            options = soup.find('select', attrs={'id': '_curriculum_search'}).find_all('option')
            _directions.extend([Direction(direction_id=opt_value, faculty_id=faculty.pk, name=option.getText().strip()) for option in options if (opt_value := option.get('value')) and not Direction.objects.filter(name=option.getText().strip()).exists()])
        Direction.objects.bulk_create(_directions)

    def years(self):
        all_years = EducationYear.objects.all()
        for direction in Direction.objects.all():
            logging.info(f'years - {direction.pk}')
            for edu_year in all_years:
                data = {
                    'depdrop_parents[0]': direction.direction_id,
                    'depdrop_parents[1]': edu_year.year_id,
                    'depdrop_all_params[_curriculum_search]': direction.direction_id,
                    'depdrop_all_params[_education_year_search]': edu_year.year_id,
                }

                try:
                    response = self.session.post('https://hemis.samdu.uz/ajax/get-semester-years', headers=self.headers_for_ajax, data=data).json()
                except:
                    continue

                time.sleep(0.5)

                if not (semestrs := response['output']): continue
                direction_edu_year, _ = DirectionEduYear.objects.get_or_create(direction=direction, edu_year=edu_year)
                
                for semestr in semestrs:
                    if (semestr_name := int(semestr['name'][0])) > 8: continue
                    semestr, _ = Semestr.objects.get_or_create(semestr=semestr_name, defaults={'semestr_id': semestr['id']})
                    direction_edu_year.semestrs.add(semestr)

                    if edu_year.current and not direction.course and (course := round(semestr.semestr / 2)) > 0:
                        direction.course = Course.objects.get_or_create(course=course)[0]
                        direction.save()
    
    def groups(self):

        for year in DirectionEduYear.objects.all():
            logging.info(f'gorups - {year.pk}')
            for semestr in year.semestrs.all():
                data = {
                    'depdrop_parents[0]': year.direction.direction_id,
                    'depdrop_parents[1]': year.edu_year.year_id,
                    'depdrop_parents[2]': semestr.semestr_id,
                    'depdrop_all_params[_curriculum_search]': year.direction.direction_id,
                    'depdrop_all_params[_education_year_search]': year.edu_year.year_id,
                    'depdrop_all_params[_semester_search]': semestr.semestr_id,
                }

                response = self.session.post('https://hemis.samdu.uz/ajax/get-group-semesters', headers=self.headers_for_ajax, data=data).json()
                
                time.sleep(0.5)

                if not (groups := response['output']): continue
                for group in groups:
                    Group.objects.get_or_create(name=group['name'], defaults={'group_id': group['id'], 'direction_id': year.direction_id})

    def creditors(self):
        
        for edu_year in EducationYear.objects.all():
            logging.info(f'CREDITORS {edu_year.year}')
            for group in Group.objects.all():
                if not (dir_eduyears := DirectionEduYear.objects.filter(direction=group.direction, edu_year=edu_year)).exists(): continue

                self.next_page = None
                for semestr in dir_eduyears.first().semestrs.all():
                    params = {
                        'FilterForm[_faculty]': group.direction.faculty.faculty_id,
                        'FilterForm[_curriculum]': group.direction.direction_id,
                        'FilterForm[_education_year]': edu_year.year_id,
                        'FilterForm[_semester]': semestr.semestr_id,
                        'FilterForm[_group]': group.group_id,
                        '_pjax': '#admin-grid',
                    }

                    response = self.session.get('https://hemis.samdu.uz/performance/debtors', params=params)
                    self.parse_creditors_table(response, group.direction, semestr, edu_year)

                    while self.next_page:
                        print(self.next_page)
                        response = self.session.get(f'https://hemis.samdu.uz{self.next_page}')
                        self.parse_creditors_table(response, group.direction, semestr, edu_year)

    def parse_creditors_table(self, response: requests.Response, direction, semestr, edu_year):
        soup = BeautifulSoup(response.text, 'html.parser')

        self.next_page = next_page_link['href'] if (pagination := soup.find('ul', attrs={'class': 'pagination'})) and (next_page_link := pagination.find('li', attrs={'class': 'next'}).find('a')) else None

        for tr in soup.find('tbody').find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2: continue

            name = tds[1].getText().strip().replace('‘', "'").replace('’', "'")
            subject_name = tds[5].getText().strip().replace('‘', "'").replace('’', "'")

            student = Student.objects.filter(name=name)
            if not (students := Student.objects.filter(name=name)).exists(): continue
            student = students.first()

            try:
                subject = Subject.objects.get(direction=direction, semestr=semestr, name=subject_name)
            except:
                logging.error(f'CREDITORS subject {subject_name} - {name}')
                continue

            if Credit.objects.filter(student=student, subject=subject, edu_year=edu_year).exists(): continue
            Credit.objects.get_or_create(student=student, subject=subject, edu_year=edu_year)


class ParseCurriculum(ParseBase):

    def __init__(self):
        self.base_url = 'https://hemis.samdu.uz'
        super().__init__()
    
    def parse(self):
        response = self.session.get(f'{self.base_url}/curriculum/curriculum-list')
        self.parse_table(response)

        while self.page:
            response = self.session.get(f'{self.base_url}{self.page}')
            self.parse_table(response)

    def parse_table(self, response: requests.Response):
        soup = BeautifulSoup(response.text, 'html.parser')

        self.page = page_li['href'] if (page_li := soup.find('ul', attrs={'class': 'pagination'}).find('li', attrs={'class': 'next'}).find('a')) else None

        for curriculum in soup.find('tbody').find_all('tr'):
            group = None

            tds = curriculum.find_all('td')

            response = self.session.get(f"{self.base_url}{tds[1].find('a')['href']}")
            soup = BeautifulSoup(response.text, 'html.parser')

            time.sleep(1)
            
            groups_td = soup.find('table', attrs={'id': 'w0'}).find_all('tr')[5].find('td')
            if not groups_td.getText(): continue

            for _group in groups_td.getText().split(';'):
                if (groups := Group.objects.filter(name=_group.strip())).exists():
                    group = groups.first()
                    break
            
            if not group: continue
            logging.info(f'curriculum - {group.pk}')

            for subject in soup.find('tbody').find_all('tr'):
                semestr = None
                
                if (_semestr := subject.find('th')):

                    if (_semestr := int(_semestr.getText()[0])) > 8:
                        semestr = None
                        continue

                    semestr = Semestr.objects.get(semestr=_semestr)
                    continue

                if not semestr: continue

                tds = subject.find_all('td')
                if not (_link := tds[1].find('a')): continue

                if not (credits := tds[4].getText().strip()): continue

                response = self.session.get(f"{self.base_url}{_link['value']}", headers=self.headers_for_ajax)
                soup = BeautifulSoup(response.text, 'html.parser')

                trs = soup.find('tbody').find_all('tr')

                hours = {
                    'hours': None,
                    'lecture_hours': None,
                    'practice_hours': None,
                    'seminar_hours': None,
                    'laboratory_hours': None,
                    'independent_hours': None
                }
                for tr in trs:
                    tds = tr.find_all('td')
                    td_name = tds[0].getText().strip().replace('‘', "'").replace('’', "'")
                    td_value = tds[1].getText().replace('soat', '').strip()
                    
                    _hours = lecture_hours if (lecture_hours := td_value.replace('soat', '').strip()) else None

                    if "Ma'ruza" in td_name: hours['lecture_hours'] = _hours
                    if 'Amaliy' in td_name: hours['practice_hours'] = _hours
                    if 'Seminar' in td_name: hours['seminar_hours'] = _hours
                    if 'Laboratoriya' in td_name: hours['laboratory_hours'] = _hours
                    if 'Mustaqil ta‘lim' in td_name: hours['independent_hours'] = _hours
                    if 'Jami' in td_name:
                        hours['hours'] = _hours
                        break
                
                if not hours['hours']: continue
                
                Subject.objects.get_or_create(
                    direction=group.direction,
                    semestr=semestr,
                    name=_link.getText().strip().replace('‘', "'").replace('’', "'"),
                    hours=hours['hours'],
                    lecture_hours=hours['lecture_hours'],
                    practice_hours=hours['practice_hours'],
                    seminar_hours=hours['seminar_hours'],
                    laboratory_hours=hours['laboratory_hours'],
                    independent_hours=hours['independent_hours'],
                    credits=credits[0]
                )
                

class ParseStudents(ParseBase):

    def __init__(self):
        self.base_url = 'https://hemis.samdu.uz'
        super().__init__()

    def parse(self):
        response = self.session.get(f'{self.base_url}/student/contingent-list')
        self.parse_table(response)

        while self.page:
            time.sleep(1)

            try:
                response = self.session.get(f'{self.base_url}{self.page}')
            except:
                continue
            self.parse_table(response)

    def parse_table(self, response: requests.Response):
        soup = BeautifulSoup(response.text, 'html.parser')

        self.page = page_li['href'] if (page_li := soup.find('ul', attrs={'class': 'pagination'}).find('li', attrs={'class': 'next'}).find('a')) else None

        for student_tr in soup.find('tbody').find_all('tr'):
            tds = student_tr.find_all('td')

            name = tds[1].getText(strip=True).replace('Erkak', '').replace('Ayol', '').replace('‘', "'").replace('’', "'")
            hemis_id = tds[2].getText(strip=True)[:12]

            try:
                group = Group.objects.get(name=tds[5].find('p').getText(strip=True))
            except:
                logging.error(f"GroupError {hemis_id} {tds[5].find('p').getText(strip=True)}")
                continue

            logging.info(f'student - {hemis_id} {name} {group.name}')

            try:
                Student.objects.get_or_create(group=group, name=name, hemis_id=hemis_id)
            except:
                logging.error(f"StudentError {hemis_id} {tds[5].find('p').getText(strip=True)}")