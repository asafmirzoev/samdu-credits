from django.core.management.base import BaseCommand
from django.utils import timezone

from credits.utils import PraseCreditorsAsync

class Command(BaseCommand):
    help = 'Displays current time'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Start at: {timezone.now()}")
        PraseCreditorsAsync().start()
        self.stdout.write(f"End at: {timezone.now()}")