from django.apps import AppConfig


class AdminConfig(AppConfig):
    name = 'ltc.admin'
    label = 'ltc.admin'

    def ready(self):
        super().ready()

        import django.contrib.admin.sites
        import django.contrib.admin.views.decorators
        from ltc.admin.sites import AdminSite
        from ltc.admin.decorators import staff_member_required
        site = AdminSite()
        django.contrib.admin.sites.site = site
        django.contrib.admin.site = site

        django.contrib.admin.views.decorators.staff_member_required = staff_member_required  # NOQA E501
