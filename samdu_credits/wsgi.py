import os

import logging
from django.core.wsgi import get_wsgi_application

from credits.utils import init_deadline

logging.basicConfig(filename='logs.log', level=logging.INFO)

init_deadline()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'samdu_credits.settings')

application = get_wsgi_application()
