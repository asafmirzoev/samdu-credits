from django import template

from credits.models import DeadLine
from credits.utils import is_deadline

register = template.Library()


@register.simple_tag(name='get_deadline')
def get_deadline():
    return deadlines.first() if (deadlines := DeadLine.objects.all()).exists() else None

@register.simple_tag(name='check_deadline')
def check_deadline():
    return is_deadline()
