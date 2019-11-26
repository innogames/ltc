from django.contrib import admin

# Register your models here.
from jltc.models import Configuration, Test, Project

class TestAdmin(admin.ModelAdmin):
    search_fields = ('display_name',)

admin.site.register(Configuration)
admin.site.register(Test, TestAdmin)
admin.site.register(Project)
