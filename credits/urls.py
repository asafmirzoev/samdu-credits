from django.urls import path, include

from .views import (
    HomeView, StudentCreditsView, DeaneryOverviewView, DeanerySearchView, DeaneryCourseView, DeaneryCourseCreditsView,
    DeaneryDirectionView, DeaneryDirectionCreditsView, DeaneryGroupView, DeaneryGroupCreditsView, DeanerySemestrView,
    DeaneryPaySubmitView, DeaneryUploadView, AccountantOverviewView, AccountantFacultyView,
    AccountantFacultyCreditsView, AccountantSearchView, AccountantCourseView, AccountantCourseCreditsView,
    AccountantDirectionView, AccountantGroupView, AccountantSemestrView, AccountantPaySubmitView,
    FinancesOverviewView, FinancesFacultyView, FinancesCourseView, FinancesDirectionView, FinancesCreditsView,
    EduPartOverviewView, EduPartSearchView, EduPartFacultyView, EduPartFacultyCreditsView, EduPartCourseView,
    EduPartCourseCreditsView, EduPartDirectionView, EduPartDirectionCreditsView, EduPartGroupView,
    EduPartGroupCreditsView, EduPartSemestrView, EduPartDeadlineView, 
    InvoicesView
)


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('credits/', StudentCreditsView.as_view(), name='student-credits'),

    path('invoices/<int:payset_id>/', InvoicesView.as_view(), name='invoices'),

    path('deanery/', include([
        path('overview/', include([
            path('', DeaneryOverviewView.as_view(), name='deanery-overview'),

            path('<int:course_id>/', DeaneryCourseView.as_view(), name='deanery-course'),
            path('<int:course_id>/credits/', DeaneryCourseCreditsView.as_view(), name='deanery-course-credits'),

            path('<int:course_id>/direction/<int:direction_id>/', DeaneryDirectionView.as_view(), name='deanery-direction'),
            path('<int:course_id>/direction/<int:direction_id>/credits/', DeaneryDirectionCreditsView.as_view(), name='deanery-direction-credits'),
            
            path('<int:course_id>/group/<int:group_id>/', DeaneryGroupView.as_view(), name='deanery-group'),
            path('<int:course_id>/group/<int:group_id>/credits/', DeaneryGroupCreditsView.as_view(), name='deanery-group-credits'),
            
            path('<int:group_id>/semestr/<int:semestr_id>/', DeanerySemestrView.as_view(), name='deanery-semestr'),
        ])),
        
        path('search/', DeanerySearchView.as_view(), name='deanery-search'),
        path('pay-submit/<int:student_id>/', DeaneryPaySubmitView.as_view(), name='deanery-pay-submit'),
        path('upload/', DeaneryUploadView.as_view(), name='deanery-upload')
    ])),

    path('accountant/', include([
        path('overview/', include([
            path('', AccountantOverviewView.as_view(), name='accountant-overview'),

            path('<int:faculty_id>/', AccountantFacultyView.as_view(), name='accountant-faculty'),
            path('<int:faculty_id>/credits/', AccountantFacultyCreditsView.as_view(), name='accountant-faculty-credits'),

            path('<int:faculty_id>/<int:course_id>/', AccountantCourseView.as_view(), name='accountant-course'),
            path('<int:faculty_id>/<int:course_id>/credits/', AccountantCourseCreditsView.as_view(), name='accountant-course-credits'),

            path('<int:course_id>/direction/<int:direction_id>/', AccountantDirectionView.as_view(), name='accountant-direction'),
            path('<int:course_id>/group/<int:group_id>/', AccountantGroupView.as_view(), name='accountant-group'),
            path('<int:group_id>/semestr/<int:semestr_id>/', AccountantSemestrView.as_view(), name='accountant-semestr'),
        ])),
        
        path('search/', AccountantSearchView.as_view(), name='accountant-search'),
        path('pay-submit/<int:payset_id>/', AccountantPaySubmitView.as_view(), name='accountant-pay-submit'),
    ])),

    path('finances/', include([
        path('overview/', include([
            path('', FinancesOverviewView.as_view(), name='finances-overview'),
            path('<int:faculty_id>/', FinancesFacultyView.as_view(), name='finances-faculty'),
            path('<int:faculty_id>/<int:course_id>/', FinancesCourseView.as_view(), name='finances-course'),
            path('<int:course_id>/direction/<int:direction_id>/', FinancesDirectionView.as_view(), name='finances-direction'),
        ])),
        path('credits/<int:direction_id>/', FinancesCreditsView.as_view(), name='finances-credits')
    ])),

    path('edu-part/', include([
        path('overview/', include([
            path('', EduPartOverviewView.as_view(), name='edu-part-overview'),

            path('<int:faculty_id>/', EduPartFacultyView.as_view(), name='edu-part-faculty'),
            path('<int:faculty_id>/credits/', EduPartFacultyCreditsView.as_view(), name='edu-part-faculty-credits'),

            path('<int:faculty_id>/<int:course_id>/', EduPartCourseView.as_view(), name='edu-part-course'),
            path('<int:faculty_id>/<int:course_id>/credits/', EduPartCourseCreditsView.as_view(), name='edu-part-course-credits'),

            path('<int:course_id>/direction/<int:direction_id>/', EduPartDirectionView.as_view(), name='edu-part-direction'),
            path('<int:course_id>/direction/<int:direction_id>/credits/', EduPartDirectionCreditsView.as_view(), name='edu-part-direction-credits'),

            path('<int:course_id>/group/<int:group_id>/', EduPartGroupView.as_view(), name='edu-part-group'),
            path('<int:course_id>/group/<int:group_id>/credits/', EduPartGroupCreditsView.as_view(), name='edu-part-group-credits'),

            path('<int:group_id>/semestr/<int:semestr_id>/', EduPartSemestrView.as_view(), name='edu-part-semestr'),
        ])),
        
        path('search/', EduPartSearchView.as_view(), name='edu-part-search'),

        path('deadline/', EduPartDeadlineView.as_view(), name='edu-part-deadline'),
        path('deadline/<int:deadline_id>/', EduPartDeadlineView.as_view(), name='edu-part-deadline'),
    ])),
]