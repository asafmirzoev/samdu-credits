import os

from django.core.wsgi import get_wsgi_application


from credits.utils import InitData, init_deadline

InitData().run()
init_deadline()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'samdu_credits.settings')

application = get_wsgi_application()
