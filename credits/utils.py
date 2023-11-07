from uuid import uuid4
import math
import asyncio
import aiohttp
import requests
import time
import pickle
import logging
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlsplit
from asgiref.sync import sync_to_async

from django.db.models import QuerySet
from django.utils import timezone
from django.conf import settings

from credits.models import (
    Faculty, Direction, Course, Group, EducationYear, Semestr, Subject, DeadLine, Credit,
    DirectionEduYear, Student
)


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
            # credit.subject.semestr.course.course,
            # credit.student.group.language,
            credit.student.group.education_form,
            credit.edu_year.year,
            credit.subject.semestr.semestr,
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

        # self.session.get(f'https://api.telegram.org/bot6292467753:AAEN0gGT5TEM4BNQA6JZE2hfYZukPPVBuwA/sendMessage?chat_id=1251050357&text={timezone.now() - start}')

    def faculties(self):

        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        current_year = int(soup.find('select', attrs={'id': '_education_year_search'}).find('option', selected=True).get('value'))

        for option in reversed(soup.find('select', attrs={'id': '_education_year_search'}).find_all('option')):
            if not (opt_value := option.get('value')): continue
            if current_year < int(opt_value) or current_year - int(opt_value) >= 4: continue

            EducationYear.objects.get_or_create(year_id=opt_value, defaults={'year': option.getText(strip=True), 'current': int(opt_value) == current_year})

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
                    semestr_name = int(semestr['name'][0])
                    course, _ = Course.objects.get_or_create(course=round(semestr_name / 2))
                    semestr, _ = Semestr.objects.get_or_create(semestr=semestr_name, defaults={'semestr_id': semestr['id'], 'course': course})
                    direction_edu_year.semestrs.add(semestr)

                    if edu_year.current:
                        direction.course = course
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

                logging.info(groups)
                for group in groups:
                    Group.objects.get_or_create(name=group['name'].strip(), defaults={'group_id': group['id'], 'direction_id': year.direction_id})

    def creditors(self):

        for edu_year in EducationYear.objects.all():
            logging.info(f'CREDITORS {edu_year.year}')
            for group in Group.objects.all():
                if not (dir_eduyears := DirectionEduYear.objects.filter(direction=group.direction, edu_year=edu_year)).exists(): continue

                logging.info(f'CREDITORS group {group.pk}')
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
                    time.sleep(0.5)
                    
                    self.parse_creditors_table(response, group.direction, semestr, edu_year)

                    while self.next_page:
                        # logging.info(self.next_page)
                        response = self.session.get(f'https://hemis.samdu.uz{self.next_page}')
                        time.sleep(0.5)
                        self.parse_creditors_table(response, group.direction, semestr, edu_year)

    def parse_creditors_table(self, response: requests.Response, direction, semestr, edu_year):

        soup = BeautifulSoup(response.text, 'html.parser')

        self.next_page = next_page_link['href'] if (pagination := soup.find('ul', attrs={'class': 'pagination'})) and (next_page_link := pagination.find('li', attrs={'class': 'next'}).find('a')) else None

        for tr in soup.find('tbody').find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2: continue

            name = tds[1].getText().strip()
            subject_name = tds[5].getText().strip()

            student = Student.objects.filter(name=name)
            if not (students := Student.objects.filter(name=name)).exists():
                continue
            student = students.first()

            try:
                subject = Subject.objects.filter(direction=direction, semestr=semestr, name=subject_name).first()
            except Exception as e:
                print(e)
                logging.error(f'CREDITORS subject {direction.name} ({direction.pk}) - {semestr.semestr} ({semestr.pk}) - {subject_name} - {name}')
                continue

            if not subject:
                logging.error(f'CREDITORS subject not found {direction.name} ({direction.pk}) - {semestr.semestr} ({semestr.pk}) - {subject_name} - {name}')
                continue

            if Credit.objects.filter(student=student, subject=subject, edu_year=edu_year).exists(): continue
            Credit.objects.get_or_create(student=student, subject=subject, edu_year=edu_year)


class ParseCurriculum(ParseBase):

    def __init__(self):
        self.base_url = 'https://hemis.samdu.uz'
        self.curriculum_url = f'{self.base_url}/curriculum/curriculum-list'
        super().__init__()

    def parse(self):
        response = self.session.get(self.curriculum_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_backend = soup.find('input', attrs={'name': '_csrf-backend'})['value']

        for direction in Direction.objects.all().filter(name='BIO_5110400_Biologiya 2020-2021'):
            start = timezone.now()

            logging.info(f'CIRRICULUM {direction.pk}')
            params = {
                '_csrf-backend': csrf_backend,
                'ECurriculum[_department]': '',
                'ECurriculum[_education_type]': '',
                'ECurriculum[_education_form]': '',
                'ECurriculum[search]': direction.name,
                '_pjax': '#admin-grid',
            }

            response = self.session.get(self.curriculum_url, params=params)

            soup = BeautifulSoup(response.text, 'html.parser')

            href = None
            try:
                for tr in soup.find('tbody').find_all('tr'):
                    cirriculum_block = tr.find('a')
                    subcirriculum_text = subcirriculum_p.getText(strip=True) if (subcirriculum_p := tr.find('p')) else ''

                    if int(tr.find_all('span')[4].getText(strip=True).replace('Guruh: ', '')) < 1: continue

                    if direction.name == cirriculum_block.getText(strip=True)[:-len(subcirriculum_text)]:
                        href = cirriculum_block['href']
                        break
            except:
                logging.error(f'CIRICULLUM нет учебного плана у {direction.pk}')
                continue

            if not href:
                logging.error(f'CIRICULLUM нет учебного плана (ссылки) у {direction.pk}')
                continue

            response = self.session.get(f'{self.base_url}{href}')
            self.parse_table(direction, response)

            logging.info(timezone.now() - start)

    def parse_table(self, direction, response: requests.Response):

        with open('test.html', 'w+', encoding='utf-8') as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, 'html.parser')

        groups_td = soup.find('table', attrs={'id': 'w0'}).find_all('tr')[5].find('td')
        if not groups_td.getText():
            time.sleep(1)
            return

        semestr = None
        for subject in soup.find('tbody').find_all('tr'):
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

            subject_info_url = _link['value']
            response = self.session.get(f"{self.base_url}{subject_info_url}", headers=self.headers_for_ajax)
            soup = BeautifulSoup(response.text, 'html.parser')

            time.sleep(0.5)
            try:
                trs = soup.find('tbody').find_all('tr')
            except:
                logging.error('SUBJECT hasnt trs')
            hours = {
                'hours': None,
                'lecture_hours': None,
                'practice_hours': None,
                'seminar_hours': None,
                'laboratory_hours': None,
                'independent_hours': None
            }
            for tr in trs:
                if not tr:
                    logging.error(tr)
                    continue
                
                tds = tr.find_all('td')
                td_name = tds[0].getText().strip()
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

            # if not hours['hours']: continue

            url_queries = dict(parse_qsl(urlsplit(subject_info_url).query))
            subject_id = url_queries.get('subject')

            Subject.objects.get_or_create(
                subject_id=subject_id,
                direction=direction,
                semestr=semestr,
                name=_link.getText().strip(),
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
            time.sleep(0.5)
            try:
                response = self.session.get(f'{self.base_url}{self.page}')
            except:
                continue
            self.parse_table(response)

    def parse_table(self, response: requests.Response):
        soup = BeautifulSoup(response.text, 'html.parser')

        self.page = page_li['href'] if (page_li := soup.find('ul', attrs={'class': 'pagination'}).find('li', attrs={'class': 'next'}).find('a')) else None
        logging.info(self.page)

        for student_tr in soup.find('tbody').find_all('tr'):
            tds = student_tr.find_all('td')

            name = tds[1].getText(strip=True).replace('Erkak', '').replace('Ayol', '')
            hemis_id = tds[2].getText(strip=True)[:12]

            try:
                group = Group.objects.get(name=tds[5].find('p').getText(strip=True))
            except:
                # logging.error(f"GroupError {hemis_id} {tds[5].find('p').getText(strip=True)}")
                continue

            try:
                Student.objects.get_or_create(group=group, name=name, hemis_id=hemis_id)
            except:
                logging.error(f"StudentError {hemis_id} {tds[5].find('p').getText(strip=True)}")



class PraseCreditorsAsync:

    def __init__(self):
        self.base_url = 'https://hemis.samdu.uz'
        self.debtors_url = f'{self.base_url}/performance/debtors'
        self.cookies = {
            '_ga': 'GA1.1.1478770975.1676192409',
            '_ga_49VTPLNPW6': 'GS1.1.1677344812.2.1.1677344843.0.0.0',
            '_ym_uid': '1676192409603276595',
            'tmr_lvid': '9e71bf292cc968b9b024e320895f4425',
            'tmr_lvidTS': '1676192408763',
            '_backendUser_8': '91fdd14232d4c573838cf919d9aead049e197c67f0a3de08f266c7fb51126e38a%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_backendUser_8%22%3Bi%3A1%3Bs%3A50%3A%22%5B%221849%22%2C%22GEguCgGsfxJkAPYl1A7UXYOzd8IwRlT8%22%2C518400%5D%22%3B%7D',
            '_ym_d': '1698727557',
            '_ym_isad': '2',
            '_ga_RF4T13JDG3': 'GS1.1.1699077988.12.1.1699078157.0.0.0',
            'backend_8': 'kg96dsaatphcjf3kjf49u6389j',
            '_csrf-backend': '28fa0cf599dc1c4d319babf2da90c6226ab830a0ba8a7428b6d97860d22979efa%3A2%3A%7Bi%3A0%3Bs%3A13%3A%22_csrf-backend%22%3Bi%3A1%3Bs%3A32%3A%22hlcjKJwUbtjWCDXeYsWDg5n9xDYAnF5O%22%3B%7D',
        }

        self.headers = {
            'authority': 'hemis.samdu.uz',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,uz;q=0.6',
            'cache-control': 'no-cache',
            # 'cookie': '_ga=GA1.1.1478770975.1676192409; _ga_49VTPLNPW6=GS1.1.1677344812.2.1.1677344843.0.0.0; _ym_uid=1676192409603276595; tmr_lvid=9e71bf292cc968b9b024e320895f4425; tmr_lvidTS=1676192408763; _backendUser_8=91fdd14232d4c573838cf919d9aead049e197c67f0a3de08f266c7fb51126e38a%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_backendUser_8%22%3Bi%3A1%3Bs%3A50%3A%22%5B%221849%22%2C%22GEguCgGsfxJkAPYl1A7UXYOzd8IwRlT8%22%2C518400%5D%22%3B%7D; _ym_d=1698727557; _ym_isad=2; _ga_RF4T13JDG3=GS1.1.1699077988.12.1.1699078157.0.0.0; backend_8=kg96dsaatphcjf3kjf49u6389j; _csrf-backend=28fa0cf599dc1c4d319babf2da90c6226ab830a0ba8a7428b6d97860d22979efa%3A2%3A%7Bi%3A0%3Bs%3A13%3A%22_csrf-backend%22%3Bi%3A1%3Bs%3A32%3A%22hlcjKJwUbtjWCDXeYsWDg5n9xDYAnF5O%22%3B%7D',
            'pragma': 'no-cache',
            'referer': 'https://hemis.samdu.uz/student/contingent-list',
            'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        }

        self.ajax_headers = {
            **self.headers,
            'x-csrf-token': 'nH3aqKdr5LJlKI8TfMSf0yHfYkjBE88SoVlYA1JIHMP0EbnC7CGT5wdc5UQ_gMe2eKw1DKYmoSvZHQFCPA4pjA==',
            'x-pjax': 'true',
            'x-pjax-container': '#admin-grid',
            'x-requested-with': 'XMLHttpRequest',
        }

    def start(self):
        logging.basicConfig(filename='logs.log', level=logging.INFO)
        asyncio.run(self.parse())
    
    async def parse(self):
        connector = aiohttp.TCPConnector(limit=2, verify_ssl=False)
        async with aiohttp.ClientSession(connector=connector, headers=self.headers, cookies=self.cookies) as session:
            # await self.parse_faculties(session)
            # await self.parse_directions(session)
            # await self.parse_direction_years(session)
            # await self.parse_groups(session)
            # await self.parse_cirriculum(session)
            # await self.parse_students(session)
            await self.parse_credits(session)
    
    async def parse_faculties(self, session: aiohttp.ClientSession):
        edu_years = []
        faculties = []

        async with session.get(self.debtors_url) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')

            current_year_id = int(soup.find('select', attrs={'id': '_education_year_search'}).find('option', selected=True).get('value'))
            for option in reversed(soup.find('select', attrs={'id': '_education_year_search'}).find_all('option')):
                if not (year_id := option.get('value')):
                    continue

                year_id = int(year_id)
                if current_year_id < year_id or current_year_id - year_id >= 4:
                    continue
                
                if not await (await sync_to_async(EducationYear.objects.filter)(year_id=year_id)).aexists():
                    edu_years.append(EducationYear(
                        year_id=year_id,
                        year=option.getText(strip=True),
                        current=year_id == current_year_id
                    ))
            
            for option in soup.find('select', attrs={'id': 'filterform-_faculty'}).find_all('option'):
                if not (faculty_id := option.get('value')) or await (await sync_to_async(Faculty.objects.filter)(faculty_id=faculty_id)).aexists():
                    continue
                faculties.append(Faculty(faculty_id=faculty_id, name=option.getText(strip=True)))
        
        await EducationYear.objects.abulk_create(edu_years)
        await Faculty.objects.abulk_create(faculties)
        edu_years.clear()
        faculties.clear()
    
    async def parse_directions(self, session: aiohttp.ClientSession):
        tasks = []

        async for faculty in Faculty.objects.aiterator():
            task = asyncio.create_task(self.parse_directions_handle(session, faculty))
            tasks.append(task)
        
        group_task = asyncio.gather(*tasks)
        results = await asyncio.wait_for(group_task, 1800)

        for directions in results:
            await Direction.objects.abulk_create(directions) 

    async def parse_directions_handle(self, session: aiohttp.ClientSession, faculty: Faculty):
        await asyncio.sleep(0.5)
        
        directions = list()
        params = {
            'FilterForm[_faculty]': faculty.faculty_id,
            'FilterForm[_curriculum]': '',
            '_pjax': '#admin-grid',
        }

        async with session.get(self.debtors_url, headers=self.ajax_headers, params=params) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')

            for option in soup.find('select', attrs={'id': '_curriculum_search'}).find_all('option'):
                if not (direction_id := option.get('value')) or await (await sync_to_async(Direction.objects.filter)(direction_id=direction_id)).aexists():
                    continue
                
                directions.append(Direction(
                    direction_id=direction_id,
                    faculty=faculty,
                    name=option.getText(strip=True)
                ))
        return directions

    async def parse_direction_years(self, session: aiohttp.ClientSession):
        tasks = []

        directions = Direction.objects.all()
        async for eduyear in EducationYear.objects.all():
            async for direction in directions:
                task = asyncio.create_task(self.parse_direction_years_handle(session, eduyear, direction))
                tasks.append(task)
        
        group_task = asyncio.gather(*tasks)
        await asyncio.wait_for(group_task, 1800)
    
    async def parse_direction_years_handle(
            self,
            session: aiohttp.ClientSession,
            eduyear: EducationYear,
            direction: Direction
        ):
        await asyncio.sleep(0.5)

        data = {
            'depdrop_parents[0]': direction.direction_id,
            'depdrop_parents[1]': eduyear.year_id,
            'depdrop_all_params[_curriculum_search]': direction.direction_id,
            'depdrop_all_params[_education_year_search]': eduyear.year_id,
        }
        async with session.post(f'{self.base_url}/ajax/get-semester-years', headers=self.ajax_headers, data=data) as response:
            output: list[dict] = (await response.json(content_type='text/html'))['output']
            if not output:
                return
            
            direction_eduyear, _ = await DirectionEduYear.objects.aget_or_create(direction=direction, edu_year=eduyear)

            for semestr in output:
                if await (semestrs_set := await sync_to_async(Semestr.objects.filter)(semestr_id=semestr.get('id'))).aexists():
                    semestr = await semestrs_set.select_related('course').afirst()
                else:
                    semestr_name = int(semestr.get('name').replace('-semestr', ''))
                    course, _ = await Course.objects.aget_or_create(course=math.ceil(semestr_name / 2))
                    semestr, _ = await Semestr.objects.select_related('course').aget_or_create(course=course, semestr=semestr_name, semestr_id=semestr.get('id'))

                if eduyear.current:
                    direction.course = semestr.course
                    await direction.asave()

                await direction_eduyear.semestrs.aadd(semestr)
    
    async def parse_groups(self, session: aiohttp.ClientSession):
        tasks = []

        async for dir_eduyear in DirectionEduYear.objects.select_related('edu_year', 'direction').all():
            async for semestr in dir_eduyear.semestrs.all():
                task = asyncio.create_task(self.parse_groups_handle(session, dir_eduyear, semestr))
                tasks.append(task)
        
        group_task = asyncio.gather(*tasks)
        results = await asyncio.wait_for(group_task, 600)

        for groups in results:
            await Group.objects.abulk_create(groups, ignore_conflicts=True)
    
    async def parse_groups_handle(
            self,
            session: aiohttp.ClientSession,
            dir_eduyear: DirectionEduYear,
            semestr: Semestr
        ):
        await asyncio.sleep(0.5)
        
        groups = list()
        data = {
            'depdrop_parents[0]': dir_eduyear.direction.direction_id,
            'depdrop_parents[1]': dir_eduyear.edu_year.year_id,
            'depdrop_parents[2]': semestr.semestr_id,
            'depdrop_all_params[_curriculum_search]': dir_eduyear.direction.direction_id,
            'depdrop_all_params[_education_year_search]': dir_eduyear.edu_year.year_id,
            'depdrop_all_params[_semester_search]': semestr.semestr_id,
        }
        async with session.post(f'{self.base_url}/ajax/get-group-semesters', headers=self.ajax_headers, data=data) as response:
            output: list[dict] = (await response.json(content_type='text/html'))['output']
            if not output:
                return
            
            for group in output:
                if not await (await sync_to_async(Group.objects.filter)(name=group.get('name'))).aexists():
                    groups.append(Group(group_id=group.get('id'), name=group.get('name').strip(), direction=dir_eduyear.direction))
        
        return groups
    
    async def parse_cirriculum(self, session: aiohttp.ClientSession):
        tasks = []

        async with session.get(f'{self.base_url}/curriculum/curriculum-list') as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            csrf_backend = soup.find('input', attrs={'name': '_csrf-backend'})['value']
        
        async for direction in Direction.objects.all():
            task = asyncio.create_task(self.parse_cirriculum_handle(session, csrf_backend, direction))
            tasks.append(task)
        
        group_task = asyncio.gather(*tasks)
        results = await asyncio.wait_for(group_task, 1800)

        for subjects in results:
            await Subject.objects.abulk_create(subjects, ignore_conflicts=True)

    async def parse_cirriculum_handle(
            self,
            session: aiohttp.ClientSession,
            csrf_backend: str,
            direction: Direction
        ) -> list:
        await asyncio.sleep(0.5)

        params = {
            '_csrf-backend': csrf_backend,
            'ECurriculum[_department]': '',
            'ECurriculum[_education_type]': '',
            'ECurriculum[_education_form]': '',
            'ECurriculum[search]': direction.name,
            '_pjax': '#admin-grid',
        }

        async with session.get(f'{self.base_url}/curriculum/curriculum-list', headers=self.ajax_headers, params=params) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            cirriculum = soup.find('tbody').find('tr', attrs={'data-key': direction.direction_id})
            
            if not cirriculum:
                logging.error(f'Direction {direction.name} hasn`t cirriculum')
                return
            
            cirriculum_link = cirriculum.find('a').get('href')
            if not cirriculum_link:
                logging.error(f'Direction {direction.name} hasn`t cirriculum link in {cirriculum}')
                return
            subjects = await self.parse_cirriculum_table(session, cirriculum_link, direction)
            return subjects
            
    async def parse_cirriculum_table(
            self,
            session: aiohttp.ClientSession,
            cirriculum_link: str,
            direction: Direction
        ) -> list:
        subjects = list()
        async with session.get(f'{self.base_url}{cirriculum_link}') as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')

            current_semestr = None
            for tr in soup.find('tbody').find_all('tr'):

                if (semestr_block := tr.find('th')):
                    semestr_name = int(semestr_block.getText(strip=True).split('-')[0])
                    current_semestr = await Semestr.objects.aget(semestr=semestr_name)
                    continue
                
                if not current_semestr:
                    logging.error(f'semestr error {cirriculum_link} ___ {tr}')
                    return
                
                if not (tr.find_all('td') and tr.find('a')):
                    continue

                if not (subject_link := tr.find('a').get('value')):
                    continue

                subject_name = tr.find('a').getText(strip=True)

                credits_count = tr.find_all('td')[-1].getText(strip=True)
                if not credits_count:
                    credits_count = None
                else:
                    credits_count = float(credits_count)

                subjects.extend(
                    await self.parse_subject_table(session, direction, subject_link, subject_name, credits_count, current_semestr)
                )
        return subjects

    async def parse_subject_table(
            self,
            session: aiohttp.ClientSession,
            direction: Direction,
            subject_link: str,
            subject_name: str,
            credits_count: str,
            semestr: Semestr
        ) -> list:
        await asyncio.sleep(0.5)

        subjects = list()
        async with session.get(f'{self.base_url}{subject_link}') as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            
            hours = {}
            for tr in soup.find('tbody').find_all('tr'):
                tds = tr.find_all('td')
                subject_type = tds[0].getText(strip=True)
                subject_type_hours = tds[1].getText(strip=True).replace('soat', '')

                if subject_type_hours == '':
                    subject_type_hours = None

                if "Ma'ruza" == subject_type:
                    hours['lecture_hours'] = subject_type_hours
                elif 'Amaliy' == subject_type:
                    hours['practice_hours'] = subject_type_hours
                elif 'Seminar' == subject_type:
                    hours['seminar_hours'] = subject_type_hours
                elif 'Laboratoriya' == subject_type:
                    hours['laboratory_hours'] = subject_type_hours
                elif 'Mustaqil ta‘lim' == subject_type:
                    hours['independent_hours'] = subject_type_hours
                elif 'Jami' == subject_type:
                    hours['hours'] = subject_type_hours
                    break
            
            url_queries = dict(parse_qsl(urlsplit(subject_link).query))
            subject_id = url_queries.get('subject')

            if not await (await sync_to_async(Subject.objects.filter)(subject_id=subject_id)).aexists():
            
                subjects.append(Subject(
                    subject_id=subject_id,
                    direction=direction,
                    semestr=semestr,
                    name=subject_name,
                    hours=hours.get('hours'),
                    lecture_hours=hours.get('lecture_hours'),
                    practice_hours=hours.get('practice_hours'),
                    seminar_hours=hours.get('seminar_hours'),
                    laboratory_hours=hours.get('laboratory_hours'),
                    independent_hours=hours.get('independent_hours'),
                    credits=credits_count
                ))
        return subjects

    async def parse_students(self, session: aiohttp.ClientSession):
        tasks = []

        async with session.get(f'{self.base_url}/student/contingent-list') as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            summary_students = int(soup.find('span', attrs={'class': 'summary'}).getText(strip=True).replace(' ta', '').split('jami ')[1].replace(u'\xa0', ''))
            pages = round(summary_students / 50)
            
            for page in range(1, pages + 1):
                task = asyncio.create_task(self.parse_students_handle(session, page))
                tasks.append(task)
        
        group_task = asyncio.gather(*tasks)
        results = await asyncio.wait_for(group_task, 3600)

        for students in results:
            await Student.objects.abulk_create(students, ignore_conflicts=True)
    
    async def parse_students_handle(
            self,
            session: aiohttp.ClientSession,
            page: int
        ) -> list:
        await asyncio.sleep(0.5)

        students = list()
        params = {
            'page': page,
            'per-page': '50',
            'sort': '_student',
            '_pjax': '#admin-grid',
        }
        async with session.get(f'{self.base_url}/student/contingent-list', params=params) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            for tr in soup.find('tbody').find_all('tr'):
                tds = tr.find_all('td')
                tds[1].find('p').decompose()
                tds[2].find('p').decompose()

                student_name = tds[1].getText(strip=True)
                hemis_id = tds[2].getText(strip=True)
                group_name = tds[5].find('p').getText(strip=True)

                if not await (await sync_to_async(Group.objects.filter)(name=group_name)).aexists():
                    logging.error(f'Group not found {tr}')
                    continue

                group = await Group.objects.aget(name=group_name)
                if not await (await sync_to_async(Student.objects.filter)(hemis_id=hemis_id)).aexists():
                    students.append(Student(
                        group=group,
                        name=student_name,
                        hemis_id=hemis_id
                    ))
        return students

    async def parse_credits(self, session: aiohttp.ClientSession):
        async for faculty in Faculty.objects.all():
            async for dir_eduyear in DirectionEduYear.objects.select_related('direction', 'direction__faculty', 'edu_year').prefetch_related('semestrs').filter(direction__faculty=faculty):
                tasks = list()
                groups: QuerySet[Group] = await sync_to_async(dir_eduyear.direction.group_set.all)()
                async for semestr in dir_eduyear.semestrs.all():
                    async for group in groups:
                        task = asyncio.create_task(self.parse_credits_handle(session, dir_eduyear, group, semestr))
                        tasks.append(task)
            
                group_task = asyncio.gather(*tasks)
                results = await asyncio.wait_for(group_task, 3600)
                
                for credits in results:
                    await Credit.objects.abulk_create(credits)
    
    async def parse_credits_handle(
            self,
            session: aiohttp.ClientSession,
            dir_eduyear: DirectionEduYear,
            group: Group,
            semestr: Semestr
        ) -> list:
        await asyncio.sleep(0.5)

        credits = list()
        params = {
            'FilterForm[_faculty]': dir_eduyear.direction.faculty.faculty_id,
            'FilterForm[_curriculum]': dir_eduyear.direction.direction_id,
            'FilterForm[_education_year]': dir_eduyear.edu_year.year_id,
            'FilterForm[_semester]': semestr.semestr_id,
            'FilterForm[_group]': group.group_id,
            '_pjax': '#admin-grid',
        }

        async with session.get(f'{self.base_url}/performance/debtors', params=params, headers=self.ajax_headers) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')

            if not soup.find('span', attrs={'class': 'summary'}):
                return

            summary_credits = int(soup.find('span', attrs={'class': 'summary'}).getText(strip=True).replace(' ta', '').split('jami ')[1].replace(u'\xa0', ''))
            pages = math.ceil(summary_credits / 50)
            
            for page in range(1, pages + 1):
                credits.extend(
                    await self.parse_credits_table(session, dir_eduyear, group, semestr, params, page)
                )
        return credits
    
    async def parse_credits_table(
            self,
            session: aiohttp.ClientSession,
            dir_eduyear: DirectionEduYear,
            group: Group,
            semestr: Semestr,
            params: dict,
            page: int
        ) -> list:
        await asyncio.sleep(0.5)

        credits = list()
        params.update({'page': page})
        async with session.get(f'{self.base_url}/performance/debtors', params=params, headers=self.ajax_headers) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            if not soup.find('tbody'): return
            for tr in soup.find('tbody').find_all('tr'):
                tds = tr.find_all('td')

                group_name = tds[2].getText(strip=True)
                if not await (groups := await sync_to_async(Group.objects.filter)(name=group_name)).aexists():
                    logging.error(f"group not found {f'{self.base_url}/performance/debtors'} {tr}")
                    continue
                student_group = await groups.afirst()

                semestr_name = int(tds[4].getText(strip=True).split('-')[0])
                if not await (semestrs := await sync_to_async(Semestr.objects.filter)(semestr=semestr_name)).aexists():
                    logging.error(f"semestr not found {f'{self.base_url}/performance/debtors'} {tr}")
                    continue
                student_semestr = await semestrs.afirst()

                if group.pk != student_group.pk or semestr.pk != student_semestr.pk:
                    logging.error('info error')
                    continue

                student_name = tds[1].getText(strip=True)
                if not await (students := await sync_to_async(Student.objects.filter)(name=student_name)).aexists():
                    logging.error(f"student not found {student_name} {f'{self.base_url}/performance/debtors'} {tr}")
                    continue
                student = await students.afirst()

                subject_name = tds[5].getText(strip=True)
                if not await (subjects := await sync_to_async(Subject.objects.filter)(name=subject_name, semestr=semestr)).aexists():
                    logging.error(f"subject not found {subject_name} {f'{self.base_url}/performance/debtors'} {tr}")
                    continue
                subject = await subjects.afirst()
                
                if not await (await sync_to_async(Credit.objects.filter)(student=student, subject=subject)).aexists():
                    credits.append(Credit(
                        student=student,
                        subject=subject,
                        edu_year=dir_eduyear.edu_year
                    ))
        return credits
