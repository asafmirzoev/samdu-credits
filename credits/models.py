from django.db import models
from django.utils import timezone

from .managers import CreditsManager, AllCreditsManager
from .choices import CreditStatuses


class Faculty(models.Model):

    faculty_id = models.CharField(max_length=16)
    name = models.CharField('Название', max_length=255, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'


class EducationYear(models.Model):

    year_id = models.CharField(max_length=16)
    year = models.CharField(max_length=64)
    current = models.BooleanField(default=False)

    def __str__(self):
        return self.year

    class Meta:
        ordering = ('year',)
        verbose_name = 'Год'
        verbose_name_plural = 'Год'


class Course(models.Model):

    course = models.PositiveSmallIntegerField('Курс')
    last_semestr = models.ForeignKey('Semestr', related_name='courses_for_last', on_delete=models.PROTECT, default=None, null=True)

    def __str__(self):
        return str(self.course)
    
    def save(self, *args, **kwargs):
        super(Course, self).save(*args, **kwargs)
        
        credits = Credit.alls.filter(student__group__direction__course=self)
        credits.update(active=False)
        if self.last_semestr:
            credits.filter(subject__semestr_id__lte=self.last_semestr.pk).update(active=True)
            

    class Meta:
        ordering = ['course']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'


class Semestr(models.Model):

    semestr_id = models.CharField(max_length=16)
    semestr = models.PositiveSmallIntegerField('Семестр')
    course = models.ForeignKey(Course, verbose_name='Курс', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.semestr)

    class Meta:
        ordering = ['semestr']
        verbose_name = 'Семестр'
        verbose_name_plural = 'Семестры'


class Direction(models.Model):
    
    direction_id = models.CharField(max_length=16)
    name = models.CharField('Имя', max_length=255, unique=True)
    faculty = models.ForeignKey(Faculty, verbose_name='Факультет', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, verbose_name='Курс', on_delete=models.CASCADE, null=True, default=None)
    
    education_form = models.CharField('Форма обучения', max_length=32)
    edu_hours = models.IntegerField(null=True, default=None)

    def __str__(self):
        return self.name

    # async def asave(self, *args, **kwargs):
    #     await super(Direction, self).asave(*args, **kwargs)
    #     if not hasattr(self, 'kontraktamount'):
    #         await KontraktAmount.objects.acreate(direction=self)

    class Meta:
        ordering = ['id']
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'


class DirectionEduYear(models.Model):

    direction = models.ForeignKey(Direction, verbose_name='Направление', on_delete=models.CASCADE)
    edu_year = models.ForeignKey(EducationYear, on_delete=models.PROTECT)
    semestrs = models.ManyToManyField(Semestr)


class Group(models.Model):

    group_id = models.CharField(max_length=16)
    name = models.CharField('Имя', max_length=255, unique=True)
    direction = models.ForeignKey(Direction, verbose_name='Направление', on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'


class Subject(models.Model):
    
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE)
    semestr = models.ForeignKey(Semestr, on_delete=models.CASCADE)
    
    subject_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=255)
    hours = models.PositiveSmallIntegerField('Часы')
    lecture_hours = models.PositiveSmallIntegerField('Часы (Лекция)', null=True, default=None)
    practice_hours = models.PositiveSmallIntegerField('Часы (Практика)', null=True, default=None)
    seminar_hours = models.PositiveSmallIntegerField('Часы (Семинар)', null=True, default=None)
    laboratory_hours = models.PositiveSmallIntegerField('Часы (Лабораторная)', null=True, default=None)
    independent_hours = models.PositiveSmallIntegerField('Часы (Самостоятельное обучение)', null=True, default=None)
    credits = models.FloatField('Кредиты')

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
        ordering = ['name']
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'


class KontraktAmount(models.Model):

    direction = models.OneToOneField(Direction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, default=None, blank=True)

    def save(self, *args, **kwargs):
        super(KontraktAmount, self).save(*args, **kwargs)

        if self.amount:
            credits = Credit.objects.filter(student__group__direction=self.direction, status__in=[CreditStatuses.DEANERY_UPLOADED, CreditStatuses.FINANCE_SETTED])

            credits_for_update = []
            for credit in credits:
                if credit.subject.credits and credit.subject.hours:
                    credit.status = CreditStatuses.FINANCE_SETTED
                    credit.amount = round((self.amount / self.direction.edu_hours) * credit.subject.credits, 2)
                    credits_for_update.append(credit)
            Credit.objects.bulk_update(credits_for_update, ['status', 'amount'])


class Credit(models.Model):

    student = models.ForeignKey(Student, verbose_name='Студент', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    edu_year = models.ForeignKey(EducationYear, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, default=None, blank=True)
    status = models.CharField(max_length=64, choices=CreditStatuses.choices, default=CreditStatuses.DEANERY_UPLOADED)
    active = models.BooleanField(default=True)

    objects = CreditsManager()
    alls = AllCreditsManager()

    class Meta:
        ordering = ['student__name']


class PaySet(models.Model):

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    credits = models.ManyToManyField(Credit)
    invoice = models.FileField(upload_to='files/invoices/%Y/%m/%d/', null=True)
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