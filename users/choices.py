from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class UserRoles(TextChoices):

    EDUPART = 'EDUPART', _('Учебная часть')
    DEKAN = 'DEKAN', _('Декан')
    FINANCE = 'FINANCE', _('Финансы')
    ACCOUNTANT = 'ACCOUNTANT', _('Бухгалтер')