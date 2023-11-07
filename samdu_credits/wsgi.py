import os

import logging
from django.core.wsgi import get_wsgi_application


logging.basicConfig(filename='logs.log', level=logging.INFO)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'samdu_credits.settings')

application = get_wsgi_application()
