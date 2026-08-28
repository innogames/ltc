from django.contrib.auth.models import User
from django.test import TestCase

from ltc.base.models import Project, Test
from ltc.controller.models import LoadGenerator


class ApiSmokeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        cls.project = Project.objects.create(name='proj', enabled=True)
        cls.test = Test.objects.create(
            project=cls.project, name='t1', status=Test.RUNNING,
        )
        LoadGenerator.objects.create(
            hostname='lg1.example.com', num_cpu='4',
            memory='8000', memory_free='4000',
            la_1='0.1', la_5='0.2', la_15='0.3',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_auth(self):
        self.client.logout()
        response = self.client.get('/api/v1/tests/')
        self.assertIn(response.status_code, (401, 403))

    def test_list_tests(self):
        response = self.client.get('/api/v1/tests/')
        self.assertEqual(response.status_code, 200)

    def test_filter_by_status(self):
        response = self.client.get('/api/v1/tests/', {'status': 'R'})
        self.assertEqual(response.status_code, 200)

    def test_retrieve_test(self):
        response = self.client.get(f'/api/v1/tests/{self.test.id}/')
        self.assertEqual(response.status_code, 200)

    def test_list_loadgenerators(self):
        response = self.client.get('/api/v1/loadgenerators/')
        self.assertEqual(response.status_code, 200)

    def test_me(self):
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], 'smoke')

    def test_schema(self):
        response = self.client.get('/api/v1/schema/')
        self.assertEqual(response.status_code, 200)
