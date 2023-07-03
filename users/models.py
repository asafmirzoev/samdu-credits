from django.db import models
from django.contrib.auth.models import AbstractUser

from .choices import UserRoles


class User(AbstractUser):

    role = models.CharField(max_length=64, choices=UserRoles.choices)
    faculty = models.ForeignKey('credits.Faculty', on_delete=models.CASCADE, null=True, default=None, blank=True)
