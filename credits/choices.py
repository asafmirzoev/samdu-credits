from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _



class EducationForms(TextChoices):

    KUNDUZGI = 'Kunduzgi', _('Дневное')
    KECHKI = 'Kechki', _('Вечернее')
    QOSHMA = "Qo'shma", _('Смешанное')


class EducationLanguages(TextChoices):

    OZBEK = 'O‘zbek', _('Узбекский')
    RUS = 'Rus', _('Русский')
    TOJIK = 'Tojik', _('Таджикский')
    INGLIZ = 'Ingliz', _('Английсикй')


class CreditStatuses(TextChoices):

    UPLOADED = 'UPLOADED', _('Загружено с HEMIS')
    DEANERY_UPLOADED = 'DEANERY_UPLOADED', _('Загружено деканатом')
    FINANCE_SETTED = 'FINANCE_SETTED', _('Цена кредита утверждена')
    DEANERY_SETPAID = 'DEANERY_SETPAID', _('Оплатил')
    ACCOUNTANT_SUBMITED = 'ACCOUNTANT_SUBMITED', _('Подтверждено бухгалтером')
    