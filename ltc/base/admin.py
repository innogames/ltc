from django.contrib import admin

# Register your models here.
from ltc.base.models import Project, Test, Configuration

# Register your models here.
admin.site.register(Project)
admin.site.register(Test)
admin.site.register(Configuration)
