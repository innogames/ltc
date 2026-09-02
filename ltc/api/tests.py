from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

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


class TestOrderingTestCase(TestCase):
    """
    Regression: the list must be ordered newest-started first with
    never-started tests LAST. Plain `-started_at` puts NULLs first on
    PostgreSQL, which filled the dashboard with dataless ghost rows.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        project = Project.objects.create(name='proj', enabled=True)
        now = timezone.now()
        cls.newest = Test.objects.create(
            project=project, name='newest', status=Test.FINISHED,
            started_at=now - timedelta(hours=1),
        )
        cls.oldest = Test.objects.create(
            project=project, name='oldest', status=Test.FINISHED,
            started_at=now - timedelta(days=3),
        )
        cls.never_started = Test.objects.create(
            project=project, name='ghost', status=Test.CREATED,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_never_started_sorts_last(self):
        ids = [
            row['id'] for row in
            self.client.get('/api/v1/tests/').json()['results']
        ]
        self.assertEqual(
            ids, [self.newest.id, self.oldest.id, self.never_started.id]
        )

    def test_started_filter_hides_ghosts(self):
        ids = [
            row['id'] for row in
            self.client.get(
                '/api/v1/tests/', {'started': 'true'}
            ).json()['results']
        ]
        self.assertNotIn(self.never_started.id, ids)
        self.assertEqual(ids, [self.newest.id, self.oldest.id])

    def test_project_enabled_filter(self):
        disabled = Project.objects.create(name='off', enabled=False)
        hidden = Test.objects.create(
            project=disabled, name='hidden', status=Test.FINISHED,
            started_at=timezone.now(),
        )
        ids = [
            row['id'] for row in
            self.client.get(
                '/api/v1/tests/', {'project_enabled': 'true'}
            ).json()['results']
        ]
        self.assertNotIn(hidden.id, ids)

    def test_page_size_param(self):
        response = self.client.get('/api/v1/tests/', {'page_size': '2'})
        self.assertEqual(len(response.json()['results']), 2)


class SparklineTestCase(TestCase):
    """stats.spark drives the dashboard row sparklines."""

    @classmethod
    def setUpTestData(cls):
        from ltc.analyzer.models import Action, TestActionAggregateData
        cls.user = User.objects.create_user('smoke', password='smoke')
        project = Project.objects.create(name='proj', enabled=True)
        action = Action.objects.create(name='act', project=project)
        now = timezone.now()
        cls.tests = []
        for i in range(4):
            test = Test.objects.create(
                project=project, name=f't{i}', status=Test.FINISHED,
                started_at=now - timedelta(hours=4 - i),
            )
            TestActionAggregateData.objects.create(
                test=test, action=action,
                # mean = weight / count = 100 + i*10
                data={'count': 100, 'weight': (100 + i * 10) * 100,
                      'errors': 0, 'mean': 100 + i * 10},
            )
            cls.tests.append(test)
        cls.newest = cls.tests[-1]

    def setUp(self):
        self.client.force_login(self.user)

    def test_spark_is_oldest_to_newest(self):
        rows = self.client.get('/api/v1/tests/').json()['results']
        newest = next(r for r in rows if r['id'] == self.newest.id)
        spark = newest['stats']['spark']
        self.assertEqual(spark, [100.0, 110.0, 120.0, 130.0])

    def test_spark_ends_at_that_test(self):
        rows = self.client.get('/api/v1/tests/').json()['results']
        second = next(r for r in rows if r['id'] == self.tests[1].id)
        # Only that test and older ones — never future runs.
        self.assertEqual(second['stats']['spark'], [100.0, 110.0])

    def test_spark_empty_without_history(self):
        empty = Project.objects.create(name='empty', enabled=True)
        test = Test.objects.create(
            project=empty, status=Test.FINISHED, started_at=timezone.now()
        )
        payload = self.client.get(f'/api/v1/tests/{test.id}/').json()
        self.assertEqual(payload['stats']['spark'], [])


class LoadGeneratorSerializationTestCase(TestCase):
    """The model stores numbers as strings; the API must emit numbers."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        LoadGenerator.objects.create(
            hostname='lg1.example.com', num_cpu='16', memory='64',
            memory_free='33.8', la_1='4.2', la_5='3.9', la_15='3.1',
            active=True,
        )
        LoadGenerator.objects.create(
            hostname='lg2.example.com', num_cpu='', memory='n/a',
            memory_free='', la_1='', la_5='', la_15='', active=False,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_numeric_fields(self):
        rows = self.client.get('/api/v1/loadgenerators/').json()
        first = next(r for r in rows if r['hostname'] == 'lg1.example.com')
        self.assertEqual(first['num_cpu'], 16)
        self.assertEqual(first['memory'], 64)
        self.assertEqual(first['memory_free'], 33.8)
        self.assertEqual(first['la_1'], 4.2)
        self.assertEqual(first['jmeter'], 0)

    def test_junk_becomes_null(self):
        rows = self.client.get('/api/v1/loadgenerators/').json()
        second = next(r for r in rows if r['hostname'] == 'lg2.example.com')
        for field in ('num_cpu', 'memory', 'memory_free', 'la_1'):
            self.assertIsNone(second[field], field)

    def test_jmeter_counts_servers(self):
        from ltc.controller.models import JmeterServer
        project = Project.objects.create(name='proj', enabled=True)
        test = Test.objects.create(project=project, status=Test.RUNNING)
        generator = LoadGenerator.objects.get(hostname='lg1.example.com')
        for port in (1099, 1100):
            JmeterServer.objects.create(
                test=test, loadgenerator=generator, pid=1, port=port,
            )
        rows = self.client.get('/api/v1/loadgenerators/').json()
        first = next(r for r in rows if r['hostname'] == 'lg1.example.com')
        self.assertEqual(first['jmeter'], 2)


class TestActionsTestCase(TestCase):
    """stop/ and publish/ guards."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        cls.project = Project.objects.create(name='proj', enabled=True)
        cls.running = Test.objects.create(
            project=cls.project, status=Test.RUNNING,
            started_at=timezone.now(),
        )
        cls.finished = Test.objects.create(
            project=cls.project, status=Test.FINISHED,
            started_at=timezone.now(),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_stop_requires_auth(self):
        self.client.logout()
        response = self.client.post(f'/api/v1/tests/{self.running.id}/stop/')
        self.assertIn(response.status_code, (401, 403))

    def test_stop_rejects_finished_test(self):
        response = self.client.post(f'/api/v1/tests/{self.finished.id}/stop/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('detail', response.json())

    def test_stop_terminates_running_test(self):
        from unittest import mock
        with mock.patch('ltc.base.models.Test.terminate') as terminate:
            response = self.client.post(
                f'/api/v1/tests/{self.running.id}/stop/'
            )
        self.assertEqual(response.status_code, 200)
        terminate.assert_called_once()

    def test_publish_without_confluence_is_503(self):
        from django.test import override_settings
        with override_settings(WIKI_URL=''):
            response = self.client.post(
                f'/api/v1/tests/{self.finished.id}/publish/'
            )
        self.assertEqual(response.status_code, 503)

    def test_publish_without_template_is_409(self):
        from django.test import override_settings
        with override_settings(WIKI_URL='https://wiki.example.com'):
            response = self.client.post(
                f'/api/v1/tests/{self.finished.id}/publish/'
            )
        self.assertEqual(response.status_code, 409)
