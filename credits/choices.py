from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class EducationForms(TextChoices):

    KUNDUZGI = 'Kunduzgi', _('Дневное')
    KECHKI = 'Kechki', _('Вечернее')


class EducationLanguages(TextChoices):

    OZBEK = 'O‘zbek', _('Узбекский')
    RUS = 'Rus', _('Русский')


class CreditStatuses(TextChoices):

    DEANERY_UPLOADED = 'DEANERY_UPLOADED', _('Загружено деканатом')
    FINANCE_SETTED = 'FINANCE_SETTED', _('Цена кредита утверждена')
    DEANERY_SETPAID = 'DEANERY_SETPAID', _('Оплатил')
    ACCOUNTANT_SUBMITED = 'ACCOUNTANT_SUBMITED', _('Подтверждено бухгалтером')
    