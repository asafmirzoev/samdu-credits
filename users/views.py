from django.http import HttpRequest, HttpResponse
from django.views import View

from . import services as svc


class UserLoginView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_login_page(request)

    def post(self, request: HttpRequest) -> HttpResponse:
        return svc.user_login(request)
    

class UserLogoutView(View):

    def post(self, request: HttpRequest) -> HttpResponse:
        return svc.user_logout(request)
