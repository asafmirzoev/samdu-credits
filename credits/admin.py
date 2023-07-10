from django.contrib import admin

from .models import (
    Faculty, Department, Teacher, Course, Direction, Group, EducationYear,
    Semestr, Subject, Student, Credit, PaySet
)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    pass

@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    pass

@admin.register(PaySet)
class PaySetAdmin(admin.ModelAdmin):
    pass
