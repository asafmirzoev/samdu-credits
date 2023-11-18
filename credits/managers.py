from django.db import models


class CreditsManager(models.Manager):
    def get_queryset(self):
        return super(CreditsManager, self).get_queryset().filter(active=True)


class AllCreditsManager(models.Manager):
    def get_queryset(self):
        return super(AllCreditsManager, self).get_queryset()