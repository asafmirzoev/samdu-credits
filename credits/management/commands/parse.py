import requests
import traceback
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from credits.utils import PraseCreditorsAsync


class Command(BaseCommand):
    help = 'Displays current time'

    def handle(self, *args, **kwargs):
        start = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{start} credits'
        requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={text}')
        self.stdout.write(f"Start at: {start}")

        try:
            PraseCreditorsAsync().start()
        except:
            err = traceback.format_exc()
            logging.error(err)
            requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={err}')

        end = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{end} credits'
        requests.get(f'https://api.telegram.org/bot6564300157:AAGAVk0XjOdjTEKisQD0iGEtmnPxlN-FDBc/sendMessage?chat_id=1251050357&text={text}')
        self.stdout.write(f"End at: {end}")