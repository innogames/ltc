from django.contrib import admin

from ltc.analyzer.models import (
    ReportTemplate,
    GraphiteVariable,
    TestData,
)


class ReportVariableInline(admin.TabularInline):
    model = GraphiteVariable


class CollectionAdmin(admin.ModelAdmin):
    save_as = True
    inlines = (ReportVariableInline,)


admin.site.register(ReportTemplate, CollectionAdmin)
admin.site.register(TestData)
