from django.contrib import admin

from .models import (
    Faculty, Department, Teacher, Course, Direction, Group, EducationYear,
    Semestr, Subject, Student, Credit
)

@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    pass
