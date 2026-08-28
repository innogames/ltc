from django.contrib.auth.models import User
from django.test import TestCase

from ltc.base import services
from ltc.base.models import Project, Test


class SpaTestCase(TestCase):
    def test_spa_routes_do_not_error(self):
        # 200 with a frontend build present, 503 without one — never 404/500.
        for route in ('/', '/analyzer', '/online'):
            response = self.client.get(route)
            self.assertIn(response.status_code, (200, 503), route)


class DashboardStatsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        cls.project = Project.objects.create(name='proj', enabled=True)
        cls.test = Test.objects.create(
            project=cls.project, name='t1', status=Test.FINISHED
        )

    def test_stats_for_test_without_data(self):
        stats = services.dashboard_test_stats([self.test])
        row = stats[self.test.id]
        self.assertEqual(row['success_requests'], 100)
        self.assertEqual(row['result'], 'success')

    def test_success_level_thresholds(self):
        self.assertEqual(services.success_level(99), 'success')
        self.assertEqual(services.success_level(96), 'warning')
        self.assertEqual(services.success_level(90), 'danger')

    def test_model_str(self):
        self.assertIn('t1', str(self.test))

    def test_vars_default_is_not_shared(self):
        t1 = Test.objects.create(project=self.project)
        t2 = Test.objects.create(project=self.project)
        t1.vars['x'] = 1
        self.assertEqual(t2.vars, {})
