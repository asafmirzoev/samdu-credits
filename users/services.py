from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.utils.translation import gettext_lazy as _

from .models import User


def get_login_page(request: HttpRequest) -> HttpResponse:
    return render(request, 'users/login.html')


def user_login(request: HttpRequest) -> HttpResponse:
    username, password = request.POST.get('username'), request.POST.get('password')
    if not ((user := User.objects.filter(username=username)).exists() and user.first().check_password(password)):
        messages.error(request, _('Неверные логин или пароль'))
        return redirect('users:login')
    
    login(request, user.first())
    return redirect('credits:home')

def user_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('users:login')