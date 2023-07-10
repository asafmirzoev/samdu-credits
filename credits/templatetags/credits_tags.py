from django import template

from credits.models import DeadLine, Student
from credits.choices import CreditStatuses
from credits.utils import is_deadline
from users.models import User
from users.choices import UserRoles

register = template.Library()


@register.simple_tag(name='get_deadline')
def get_deadline(user: User):
    if user.role == UserRoles.DEKAN: return DeadLine.objects.get(faculty_id=user.faculty.pk)
    if user.role == UserRoles.ACCOUNTANT: return DeadLine.objects.get(for_accountant=True)
    if user.role == UserRoles.FINANCE: return DeadLine.objects.get(for_finances=True)
    return None

@register.simple_tag(name='check_deadline')
def check_deadline(user: User):
    if user.role == UserRoles.DEKAN: return is_deadline(faculty_id=user.faculty.pk)
    if user.role == UserRoles.ACCOUNTANT: return is_deadline(for_accountant=True)
    if user.role == UserRoles.FINANCE: return is_deadline(for_finances=True)
    return False


@register.simple_tag(name='deanery_get_valid_credits')
def deanery_get_valid_credits(student):
    return student.credit_set.filter(status=CreditStatuses.FINANCE_SETTED)
