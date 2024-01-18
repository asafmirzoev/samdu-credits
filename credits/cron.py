import requests
import traceback
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from credits.utils import PraseCreditorsAsync


def parse():
    start = timezone.now()
    text = f'{start} eval'
    requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={text}')

    try:
        PraseCreditorsAsync().start()
    except:
        err = traceback.format_exc()
        logging.error(err)
        requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={err}')

    end = timezone.now()
    text = f'{end} eval'
    requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={text}')
