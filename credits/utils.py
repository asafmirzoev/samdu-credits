from uuid import uuid4
import io
import math
import asyncio
import aiohttp
import requests
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
from credits.choices import CreditStatuses


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
            credit.student.group.direction.education_form,
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


def students_to_excel(students: QuerySet[Student]):
    import pandas as pd

    data = [
        [
            i + 1,
            student.hemis_id,
            student.name,
            student.group.direction.name,
            amount
        ] for i, student in enumerate(students) if (amount := sum([credit.amount for credit in student.credit_set.filter(status__in=[CreditStatuses.DEANERY_SETPAID, CreditStatuses.ACCOUNTANT_SUBMITED]) if credit.amount]))
    ]
    buffer = io.BytesIO()
    df = pd.DataFrame(data)

    # filename = settings.BASE_DIR / f'files/buxgalter/students-{uuid4()}.xlsx'
    df.to_excel(buffer, header=False, index=False)
    buffer.seek(0)
    return buffer


def submited_credits_to_excel(credits: QuerySet[Credit]):
    import pandas as pd

    data = [
        [
            i,
            credit.student.hemis_id,
            credit.student.name,
            credit.student.group.direction.name,
            credit.student.group.name,
            credit.subject.name,
            credit.subject.semestr.course.course,
            '',
            credit.student.group.direction.education_form,
            credit.edu_year.year,
            credit.subject.semestr.semestr,
            '',
            '',
            credit.student.group.direction.edu_hours,
            credit.subject.hours,
            credit.subject.lecture_hours,
            credit.subject.practice_hours,
            credit.subject.seminar_hours,
            credit.subject.laboratory_hours,
            credit.subject.independent_hours,
            credit.subject.credits,
        ] for i, credit in enumerate(credits, 1)
    ]

    buffer = io.BytesIO()
    df = pd.DataFrame(data)

    # filename = settings.BASE_DIR / f'files/buxgalter/credits-{uuid4()}.xlsx'
    df.to_excel(buffer, header=False, index=False)
    buffer.seek(0)
    return buffer


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
            '_ym_d': '1698727557',
            '_ga_RF4T13JDG3': 'GS1.1.1702960069.16.1.1702961441.0.0.0',
            '_backendUser_8': 'cbaa03a4b48a1639bee2a1753a845aec36ac396398b36bb1c48d9008e4ac095ba%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_backendUser_8%22%3Bi%3A1%3Bs%3A48%3A%22%5B%221849%22%2C%22uhVX91JI_EIEJpX9EoaoFIcR-pJzqaOG%22%2C3600%5D%22%3B%7D',
            '_csrf-backend': '7bbe2c97992d0b6334d4a849f02edda64fe8af82a54d8e4ae85ed90c9d0069b4a%3A2%3A%7Bi%3A0%3Bs%3A13%3A%22_csrf-backend%22%3Bi%3A1%3Bs%3A32%3A%225LIEj0uivyP8gu2aD1Qt23qGaUZ-33kT%22%3B%7D',
            'backend_8': 'n4uuarhqab25c433jkk729hurs',
        }



        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        }

        self.ajax_headers = {
            **self.headers,
            'x-csrf-token': 'ayPSEn6v9FR2_oVKTV3wb1nP3FfteNZFIM7PAUVvB3leb5tXFJ-BPQCH1XIqKMIOHf6NI99LpwJBm5UsdlxsLQ==',
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

            requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text=parse ended')
    
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
            await Direction.objects.abulk_create(directions, ignore_conflicts=True) 

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
            
            # for i in range(1160):
            #     try:
            direction_eduyear, _ = await DirectionEduYear.objects.aget_or_create(direction=direction, edu_year=eduyear)
                # except:
                #     continue

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

            education_form = None
            edu_hours = None
            for tr in soup.find('table', id='w0').find_all('tr'):
                th = tr.find('th').getText(strip=True)
                td = tr.find('td').getText(strip=True)

                if th == 'Ta’lim shakli':
                    education_form = td
                    if education_form in ['Qo‘shma', 'Kunduzgi', 'Magistr']:
                        edu_hours = 60
                    elif education_form == 'Kechki':
                        edu_hours = 56
                    elif education_form == 'Sirtqi':
                        edu_hours = 48
            
            if education_form and edu_hours:
                direction.education_form = education_form
                direction.edu_hours = edu_hours
                await direction.asave()
            else:
                logging.error(f'education form error {cirriculum_link}')
                return

            current_semestr = None
            for tr in soup.find('tbody').find_all('tr'):

                if (semestr_block := tr.find('th')):
                    semestr_name = int(semestr_block.getText(strip=True).split('-')[0])
                    current_semestr = await Semestr.objects.aget(semestr=semestr_name)
                    continue
                
                if not current_semestr:
                    logging.error(f'semestr error {cirriculum_link} ___ {tr}')
                    return
                
                if not ((tds := tr.find_all('td')) and tr.find('a')):
                    logging.error(f'error 1 {cirriculum_link} ___ {tr}')
                    continue

                if not (subject_link := tr.find('a').get('value')):
                    logging.error(f'error 2 {cirriculum_link} ___ {tr}')
                    continue

                subject_name = tr.find('a').getText(strip=True)

                credits_count = tds[-1].getText(strip=True)
                if not credits_count:
                    logging.error(f'credits is null {cirriculum_link} ___ {tr}')
                    continue

                hours = tds[-2].getText(strip=True)
                if not hours:
                    logging.error(f'hours is null {cirriculum_link} ___ {tr}')
                    continue

                credits_count = float(credits_count)
                hours = int(hours)

                if not credits_count and hours:
                    credits_count = int(hours / 30)
                
                subjects.extend(
                    await self.parse_subject_table(session, direction, subject_link, subject_name, hours, credits_count, current_semestr)
                )
        return subjects

    async def parse_subject_table(
            self,
            session: aiohttp.ClientSession,
            direction: Direction,
            subject_link: str,
            subject_name: str,
            hours: int,
            credits_count: float,
            semestr: Semestr
        ) -> list:
        await asyncio.sleep(0.5)

        subjects = list()
        async with session.get(f'{self.base_url}{subject_link}') as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            
            hours_dict = {}
            for tr in soup.find('tbody').find_all('tr'):
                tds = tr.find_all('td')
                subject_type = tds[0].getText(strip=True)
                subject_type_hours = tds[1].getText(strip=True).replace('soat', '')

                if subject_type_hours == '':
                    subject_type_hours = None

                if "Ma’ruza" == subject_type:
                    hours_dict['lecture_hours'] = subject_type_hours
                elif 'Amaliy' == subject_type:
                    hours_dict['practice_hours'] = subject_type_hours
                elif 'Seminar' == subject_type:
                    hours_dict['seminar_hours'] = subject_type_hours
                elif 'Laboratoriya' == subject_type:
                    hours_dict['laboratory_hours'] = subject_type_hours
                elif 'Mustaqil ta‘lim' == subject_type:
                    hours_dict['independent_hours'] = subject_type_hours
                elif 'Jami' == subject_type:
                    hours_dict['hours'] = subject_type_hours
                    break
            
            url_queries = dict(parse_qsl(urlsplit(subject_link).query))
            subject_id = url_queries.get('subject')

            if not await (_subjects := await sync_to_async(Subject.objects.filter)(subject_id=subject_id)).aexists():
            
                subjects.append(Subject(
                    subject_id=subject_id,
                    direction=direction,
                    semestr=semestr,
                    name=subject_name,
                    hours=hours,
                    lecture_hours=hours_dict.get('lecture_hours'),
                    practice_hours=hours_dict.get('practice_hours'),
                    seminar_hours=hours_dict.get('seminar_hours'),
                    laboratory_hours=hours_dict.get('laboratory_hours'),
                    independent_hours=hours_dict.get('independent_hours'),
                    credits=credits_count
                ))
            else:
                await _subjects.aupdate(
                    hours=hours,
                    lecture_hours=hours_dict.get('lecture_hours'),
                    practice_hours=hours_dict.get('practice_hours'),
                    seminar_hours=hours_dict.get('seminar_hours'),
                    laboratory_hours=hours_dict.get('laboratory_hours'),
                    independent_hours=hours_dict.get('independent_hours'),
                    credits=credits_count
                )

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
        await (await sync_to_async(Credit.objects.all)()).aupdate(active=False)
        async for faculty in Faculty.objects.filter(pk=9):
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
                if not await (subjects := await sync_to_async(Subject.objects.filter)(name=subject_name, semestr=semestr, direction=dir_eduyear.direction)).aexists():
                    logging.error(f"subject not found {subject_name} {f'{self.base_url}/performance/debtors'} {tr}")
                    continue
                subject = await subjects.afirst()
                
                if not await (credits_ := await sync_to_async(Credit.objects.filter)(student=student, subject=subject)).aexists():
                    credits.append(Credit(
                        student=student,
                        subject=subject,
                        edu_year=dir_eduyear.edu_year
                    ))
                else:
                    credits_.update(active=True)
        return credits
