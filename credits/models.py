from django.db import models
from django.utils import timezone

from .choices import EducationForms, EducationLanguages, CreditStatuses


class Faculty(models.Model):

    name = models.CharField('Название', max_length=255, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'


class Department(models.Model):

    name = models.CharField('Название', max_length=255, unique=True)
    faculty = models.ForeignKey(Faculty, verbose_name='Факультет', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Кафедра'
        verbose_name_plural = 'Кафедры'


class Teacher(models.Model):

    name = models.CharField('Имя', max_length=255, unique=True)
    department = models.ForeignKey(Department, verbose_name='Кафедра', on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'


class Course(models.Model):

    course = models.PositiveSmallIntegerField('Курс')

    def __str__(self):
        return str(self.course)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'


class Semestr(models.Model):

    semestr = models.PositiveSmallIntegerField('Семестр')
    course = models.ForeignKey(Course, verbose_name='Курс', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.semestr)

    class Meta:
        ordering = ['semestr']
        verbose_name = 'Семестр'
        verbose_name_plural = 'Семестры'


class Direction(models.Model):

    name = models.CharField('Имя', max_length=255, unique=True)
    faculty = models.ForeignKey(Faculty, verbose_name='Факультет', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, verbose_name='Курс', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Direction, self).save(*args, **kwargs)
        if not hasattr(self, 'kontraktamount'):
            KontraktAmount.objects.create(direction=self)
            


    class Meta:
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'


class Group(models.Model):

    name = models.CharField('Имя', max_length=255, unique=True)
    direction = models.ForeignKey(Direction, verbose_name='Направление', on_delete=models.CASCADE)
    education_form = models.CharField('Форма обучения', max_length=32, choices=EducationForms.choices)
    language = models.CharField('Язык обучения', max_length=32, choices=EducationLanguages.choices)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'


class EducationYear(models.Model):

    year = models.CharField(max_length=64)

    def __str__(self):
        return self.year

    class Meta:
        ordering = ('year',)
        verbose_name = 'Год'
        verbose_name_plural = 'Год'


class Subject(models.Model):
    
    name = models.CharField(max_length=255)
    hours = models.PositiveSmallIntegerField('Часы')
    lecture_hours = models.PositiveSmallIntegerField('Часы (Лекция)', null=True, default=None)
    practice_hours = models.PositiveSmallIntegerField('Часы (Практика)', null=True, default=None)
    seminar_hours = models.PositiveSmallIntegerField('Часы (Семинар)', null=True, default=None)
    laboratory_hours = models.PositiveSmallIntegerField('Часы (Лабораторная)', null=True, default=None)
    independent_hours = models.PositiveSmallIntegerField('Часы (Самостоятельное обучение)', null=True, default=None)
    credits = models.PositiveSmallIntegerField('Кредиты')

    def __str__(self):
        return f'{self.name}'
    
    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
    

class Student(models.Model):

    group = models.ForeignKey(Group, verbose_name='Группа', on_delete=models.CASCADE)
    name = models.CharField('Имя', max_length=255)
    hemis_id = models.CharField('Hemis ID', max_length=255, unique=True)

    def __str__(self):
        return self.name
    
    @property
    def has_payed_credit(self):
        return self.credit_set.filter(status=CreditStatuses.FINANCE_SETTED).exists()
    
    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'


class KontraktAmount(models.Model):

    direction = models.OneToOneField(Direction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, default=None, blank=True)


class Credit(models.Model):

    student = models.ForeignKey(Student, verbose_name='Студент', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semestr = models.ForeignKey(Semestr, on_delete=models.PROTECT)
    edu_year = models.ForeignKey(EducationYear, on_delete=models.PROTECT)
    edu_hours = models.PositiveSmallIntegerField('Часы за год')
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, default=None, blank=True)
    status = models.CharField(max_length=64, choices=CreditStatuses.choices, default=CreditStatuses.DEANERY_UPLOADED)

    class Meta:
        ordering = ['id']


class PaySet(models.Model):

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    credits = models.ManyToManyField(Credit)
    pay_time = models.DateField()
    submited = models.BooleanField(default=False)

    @property
    def amount(self):
        return sum(self.credits.values_list('amount', flat=True))


class DeadLine(models.Model):

    date = models.DateTimeField(default=timezone.now)
    faculty = models.ForeignKey(Faculty, verbose_name='Факультет', on_delete=models.CASCADE, null=True, default=None, blank=True)
    for_accountant = models.BooleanField(default=False)
    for_finances = models.BooleanField(default=False)