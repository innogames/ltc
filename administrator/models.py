from __future__ import unicode_literals

from django.db import models

# Create your models here.



class JMeterProfile(models.Model):
    name = models.CharField(max_length=1000, default="")
    path = models.CharField(max_length=1000, default="")
    version = models.CharField(max_length=1000, default="")
    jvm_args_main = models.CharField(max_length=1000, default="-Xms2g -Xmx2g")
    jvm_args_jris = models.CharField(max_length=1000, default="-Xms2g -Xmx2g")

    class Meta:
        db_table = 'jmeter_profile'


class Configuration(models.Model):
    name = models.CharField(max_length=1000, default="")
    value = models.CharField(max_length=1000, default="")
    description = models.CharField(max_length=1000, default="")
    secure = models.BooleanField(default=False)

    class Meta:
        db_table = 'configuration'


class SSHKey(models.Model):
    path = models.CharField(max_length=1000, default="")
    description = models.CharField(max_length=1000, default="")
    default = models.BooleanField(default=True)
    class Meta:
        db_table = 'ssh_key'


class User(models.Model):
    login = models.CharField(max_length=100)

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.login
