from django.contrib import admin
from django.urls import path, include
from django.views.i18n import JavaScriptCatalog


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('', include(('credits.urls', 'credits'), namespace='credits'))
]
