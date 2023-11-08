from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from users.choices import UserRoles
from credits.utils import is_deadline


class SetUserLoginMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        avialable_urls = ['/credits/', '/credits', '/users/login', '/users/login/', '/jsi18n/', '/i18n/']
        if not (request.user.is_authenticated or request.path in avialable_urls):
            return redirect('users:login')
                
        if request.user.is_authenticated:

            if request.path in ['/users/login', '/users/login/']:
                return redirect('credits:home')

            if request.path != '/' and '/invoices/' not in request.path and request.path != '/users/logout/' and ((request.user.role == UserRoles.DEKAN and '/deanery' not in request.path) or (request.user.role == UserRoles.ACCOUNTANT and '/accountant' not in request.path) or (request.user.role == UserRoles.FINANCE and '/finances' not in request.path) or (request.user.role == UserRoles.EDUPART and '/edu-part' not in request.path)):
                return redirect('credits:home')
        
    def process_response(self, request, response):
        return response