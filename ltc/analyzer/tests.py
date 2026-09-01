from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from ltc.analyzer import services
from ltc.analyzer.models import (
    Action,
    TestActionAggregateData,
    TestData,
    TestDataResolution,
)
from ltc.base.models import Project, Test

AGGREGATE = {
    'mean': 100.0, '50%': 90.0, '75%': 110.0, '90%': 120.0,
    'max': 200.0, 'min': 10.0, 'count': 1000, 'errors': 5,
    'std': 15.0, 'weight': 100000.0,
}


def make_project_with_two_tests():
    project = Project.objects.create(name='proj', enabled=True)
    now = timezone.now()
    test_a = Test.objects.create(
        project=project, name='a', status=Test.FINISHED,
        started_at=now - timedelta(hours=2),
    )
    test_b = Test.objects.create(
        project=project, name='b', status=Test.FINISHED,
        started_at=now - timedelta(hours=1),
    )
    action = Action.objects.create(name='act', project=project)
    resolution = TestDataResolution.objects.create(
        frequency='1Min', per_sec_divider=60
    )
    for t in (test_a, test_b):
        TestActionAggregateData.objects.create(
            test=t, action=action, data=dict(AGGREGATE)
        )
        TestData.objects.create(
            test=t,
            data_resolution=resolution,
            data={
                'timestamp': (t.started_at.isoformat()),
                'mean': 100.0,
                'median': 90.0,
                'count': 600,
            },
        )
    return project, test_a, test_b, action


class ServicesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        (cls.project, cls.test_a, cls.test_b, cls.action) = (
            make_project_with_two_tests()
        )

    def test_compare_table(self):
        table = services.compare_table([self.test_b, self.test_a])
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]['name'], 'act')
        self.assertEqual(table[0]['mean_1'], table[0]['mean_2'])

    def test_compare_highlights_identical_tests_have_none(self):
        highlights = services.compare_highlights([self.test_b, self.test_a])
        self.assertEqual(highlights['critical'], [])
        self.assertEqual(highlights['success'], [])
        self.assertEqual(highlights['warning'], [])

    def test_resolve_compare_tests_defaults_to_prev(self):
        tests = services.resolve_compare_tests([self.test_b.id, 0])
        self.assertEqual(tests[0].id, self.test_b.id)
        self.assertEqual(tests[1].id, self.test_a.id)

    def test_action_details_data(self):
        data = services.action_details_data(self.test_b.id, self.action.id)
        self.assertEqual(data['action'].id, self.action.id)
        self.assertEqual(len(data['action_data']), 2)
        row = data['action_data'][0]
        self.assertLessEqual(row['q1'], row['q2'])
        self.assertLessEqual(row['q2'], row['q3'])

    def test_errors_level_bands(self):
        self.assertEqual(
            services._errors_level({'errors': 0, 'count': 100}), 'ok'
        )
        self.assertEqual(
            services._errors_level({'errors': 5, 'count': 100}), 'warn'
        )
        self.assertEqual(
            services._errors_level({'errors': 15, 'count': 100}), 'crit'
        )


class ReportApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('smoke', password='smoke')
        (cls.project, cls.test_a, cls.test_b, cls.action) = (
            make_project_with_two_tests()
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_report_endpoint(self):
        response = self.client.get(f'/api/v1/tests/{self.test_b.id}/report/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['test_id'], self.test_b.id)
        self.assertEqual(len(payload['test_action_aggregate_data']), 1)
        row = payload['test_action_aggregate_data'][0]
        self.assertEqual(row['action'], 'act')
        self.assertEqual(row['errors_level'], 'ok')
        self.assertEqual(len(payload['compare_data']), 2)

    def test_compare_endpoint(self):
        response = self.client.get(
            f'/api/v1/tests/{self.test_b.id}/compare/0/'
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['compare_table']), 1)
        self.assertEqual(
            [t['id'] for t in payload['tests']],
            [self.test_b.id, self.test_a.id],
        )

    def test_action_details_endpoint(self):
        response = self.client.get(
            f'/api/v1/tests/{self.test_b.id}/actions/{self.action.id}/'
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['action']['name'], 'act')
        self.assertEqual(len(payload['action_data']), 2)

    def test_report_for_test_without_started_at(self):
        # A created-but-never-started test has started_at=None; the report
        # must not crash on the previous-tests lookup.
        test = Test.objects.create(project=self.project, status=Test.CREATED)
        response = self.client.get(f'/api/v1/tests/{test.id}/report/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['test_id'], test.id)

    def test_prev_test_without_started_at(self):
        test = Test.objects.create(project=self.project, status=Test.CREATED)
        self.assertIsNotNone(test.prev_test())
