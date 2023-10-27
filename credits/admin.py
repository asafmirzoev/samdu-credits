from django.contrib import admin

from .models import (
    Faculty, Course, Direction, Group, EducationYear,
    Semestr, Subject, Student, Credit, PaySet, KontraktAmount
)

@admin.register(Faculty)
class StudentAdmin(admin.ModelAdmin):
    pass


@admin.register(Direction)
class StudentAdmin(admin.ModelAdmin):
    pass

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass

@admin.register(Group)
class StudentAdmin(admin.ModelAdmin):
    pass

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    pass

@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    pass

@admin.register(PaySet)
class PaySetAdmin(admin.ModelAdmin):
    pass

@admin.register(KontraktAmount)
class KontraktAmountAdmin(admin.ModelAdmin):
    pass
