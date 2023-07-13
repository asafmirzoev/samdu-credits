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
        if request.user.is_authenticated and (request.path in ['/credits/', '/credits'] or '/admin/' in request.path or '/logout/' in request.path or '/jsi18n/' in request.path or '/i18n/' in request.path): return

        # if not request.user.is_authenticated and (request.path != reverse('users:login') and request.path != '/'):
        #     return redirect('users:login')
        
        if request.user.is_authenticated:

            if request.path == reverse('users:login'):
                return redirect('credits:home')

            if request.path != '/' and ((request.user.role == UserRoles.DEKAN and '/deanery' not in request.path) or (request.user.role == UserRoles.ACCOUNTANT and '/accountant' not in request.path) or (request.user.role == UserRoles.FINANCE and '/finances' not in request.path) or (request.user.role == UserRoles.EDUPART and '/edu-part' not in request.path)): return redirect('credits:home')

            # if is_deadline(): messages.error(request, _('Время обработки кредитов вышло'))
        
    def process_response(self, request, response):
        return response