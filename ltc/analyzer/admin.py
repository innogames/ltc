from django.contrib import admin

# Register your models here.
from ltc.analyzer.models import Test, Project


class TestAdmin(admin.ModelAdmin):
    search_fields = ('display_name',)

admin.site.register(Test, TestAdmin)
admin.site.register(Project)
