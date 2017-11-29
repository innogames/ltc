from django.contrib import admin

# Register your models here.
from models import Test, Project


class TestAdmin(admin.ModelAdmin):
    search_fields = ('display_name',)

admin.site.unregister(Test)
admin.site.unregister(Project)
admin.site.register(Test, TestAdmin)
admin.site.register(Project)
