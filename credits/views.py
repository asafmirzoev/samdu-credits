from django.views import View
from django.http import HttpRequest, HttpResponse, Http404


from . import services as svc


class HomeView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_home_page(request)


class StudentCreditsView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_student_credits_page(request)

    def post(self, request: HttpRequest) -> HttpResponse:
        return svc.student_credits(request)
    

class InvoicesView(View):

    def get(self, request: HttpRequest, payset_id: int) -> HttpResponse:
        return svc.get_invoice(payset_id)
    

class DeaneryOverviewView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_deanery_overview_page(request)


class DeanerySearchView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_deanery_search_page(request)


class DeaneryCourseView(View):

    def get(self, request: HttpRequest, course_id: int) -> HttpResponse:
        return svc.get_deanery_course_page(request, course_id)
    

class DeaneryCourseCreditsView(View):

    def get(self, request: HttpRequest, course_id: int) -> HttpResponse:
        return svc.get_deanery_course_credits_page(request, course_id)


class DeaneryDirectionView(View):

    def get(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_deanery_direction_page(request, course_id, direction_id)


class DeaneryDirectionCreditsView(View):

    def get(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_deanery_direction_credits_page(request, course_id, direction_id)
    

class DeaneryGroupView(View):

    def get(self, request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
        return svc.get_deanery_group_page(request, course_id, group_id)


class DeaneryGroupCreditsView(View):

    def get(self, request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
        return svc.get_deanery_group_credits_page(request, course_id, group_id)


class DeanerySemestrView(View):

    def get(self, request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
        return svc.get_deanery_semestr_page(request, group_id, semestr_id)


class DeaneryPaySubmitView(View):

    def post(self, request: HttpRequest, student_id: int) -> HttpResponse:
        return svc.deanery_pay_submit(request, student_id)


class DeaneryUploadView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_deanery_upload_page(request)
    
    def post(self, request: HttpRequest) -> HttpResponse:
        return svc.deanery_upload(request)


class AccountantOverviewView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_accountant_overview_page(request)
    

class AccountantSearchView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_accountant_search_page(request)


class AccountantFacultyView(View):

    def get(self, request: HttpRequest, faculty_id: int) -> HttpResponse:
        return svc.get_accountant_faculty_page(request, faculty_id)


class AccountantFacultyCreditsView(View):

    def get(self, request: HttpRequest, faculty_id: int) -> HttpResponse:
        return svc.get_accountant_faculty_credits_page(request, faculty_id)


class AccountantCourseView(View):

    def get(self, request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
        return svc.get_accountant_course_page(request, faculty_id, course_id)


class AccountantCourseCreditsView(View):

    def get(self, request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
        return svc.get_accountant_course_credits_page(request, faculty_id, course_id)


class AccountantDirectionView(View):

    def get(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_accountant_direction_page(request, course_id, direction_id)
    

class AccountantGroupView(View):

    def get(self, request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
        return svc.get_accountant_group_page(request, course_id, group_id)


class AccountantSemestrView(View):

    def get(self, request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
        return svc.get_accountant_semestr_page(request, group_id, semestr_id)


class AccountantPaySubmitView(View):

    def post(self, request: HttpRequest, payset_id: int) -> HttpResponse:
        return svc.accountant_pay_submit(request, payset_id)


class FinancesOverviewView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_finances_overview_page(request)


class FinancesFacultyView(View):

    def get(self, request: HttpRequest, faculty_id: int) -> HttpResponse:
        return svc.get_finances_faculty_page(request, faculty_id)
    

class FinancesCourseView(View):

    def get(self, request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
        return svc.get_finances_course_page(request, faculty_id, course_id)


class FinancesDirectionView(View):

    def post(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_finances_direction_page(request, course_id, direction_id)


class FinancesCreditsView(View):

    def get(self, request: HttpRequest, direction_id: int) -> HttpResponse:
        return svc.get_finances_credits_page(request, direction_id)
    

class EduPartOverviewView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_edupart_overview_page(request)
    

class EduPartSearchView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_edupart_search_page(request)
    
    def post(self, request: HttpRequest) -> HttpResponse:
        return svc.download_edupart_search_results(request)


class EduPartFacultyView(View):

    def get(self, request: HttpRequest, faculty_id: int) -> HttpResponse:
        return svc.get_edupart_faculty_page(request, faculty_id)


class EduPartFacultyCreditsView(View):

    def get(self, request: HttpRequest, faculty_id: int) -> HttpResponse:
        return svc.get_edupart_faculty_credits_page(request, faculty_id)


class EduPartCourseView(View):

    def get(self, request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
        return svc.get_edupart_course_page(request, faculty_id, course_id)


class EduPartCourseCreditsView(View):

    def get(self, request: HttpRequest, faculty_id: int, course_id: int) -> HttpResponse:
        return svc.get_edupart_course_credits_page(request, faculty_id, course_id)


class EduPartDirectionView(View):

    def get(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_edupart_direction_page(request, course_id, direction_id)
    

class EduPartDirectionCreditsView(View):

    def get(self, request: HttpRequest, course_id: int, direction_id: int) -> HttpResponse:
        return svc.get_edupart_direction_cerdits_page(request, course_id, direction_id)
    

class EduPartGroupView(View):

    def get(self, request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
        return svc.get_edupart_group_page(request, course_id, group_id)


class EduPartGroupCreditsView(View):

    def get(self, request: HttpRequest, course_id: int, group_id: int) -> HttpResponse:
        return svc.get_edupart_group_credits_page(request, course_id, group_id)


class EduPartSemestrView(View):

    def get(self, request: HttpRequest, group_id: int, semestr_id: int) -> HttpResponse:
        return svc.get_edupart_semestr_page(request, group_id, semestr_id)


class EduPartDeadlineView(View):

    def get(self, request: HttpRequest) -> HttpResponse:
        return svc.get_edupart_deadline_page(request)
    
    def post(self, request: HttpRequest, deadline_id: int) -> HttpResponse:
        return svc.set_edupart_deadline_page(request, deadline_id)