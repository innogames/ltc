from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase

from ltc.base.models import Project, Test
from ltc.online import services


class RefreshThrottleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name='proj', enabled=True)
        cls.test = Test.objects.create(
            project=cls.project, name='t1', status=Test.RUNNING
        )

    def setUp(self):
        cache.clear()

    def test_refresh_runs_once_per_cooldown(self):
        with mock.patch(
            'ltc.online.services.TestOnlineData.update'
        ) as update:
            self.assertTrue(services.refresh_online_data(self.test))
            self.assertFalse(services.refresh_online_data(self.test))
            self.assertEqual(update.call_count, 1)


class OnlineApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        cls.project = Project.objects.create(name='proj', enabled=True)
        cls.test = Test.objects.create(
            project=cls.project, name='t1', status=Test.RUNNING
        )

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)

    def test_online_endpoint(self):
        # No result file exists, so the refresh is a no-op inside update().
        response = self.client.get(f'/api/v1/tests/{self.test.id}/online/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['online_data'], [])
