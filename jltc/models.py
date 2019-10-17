from django.db import models


class Configuration(models.Model):
    name = models.TextField()
    value = models.TextField()
    description = models.TextField()

    def __str__(self):
        return self.name