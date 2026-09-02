import logging

from django.conf import settings
from django.db.models import Count, F
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ltc.analyzer import monitoring as analyzer_monitoring
from ltc.analyzer import services as analyzer_services
from ltc.api.serializers import (
    LoadGeneratorSerializer,
    ProjectSerializer,
    TestOnlineSerializer,
    TestSerializer,
    UserSerializer,
)
from ltc.base import services as base_services
from ltc.base.models import Project, Test
from ltc.controller.models import LoadGenerator
from ltc.online import services as online_services

logger = logging.getLogger('django')


class TestPagination(PageNumberPagination):
    """Lets the SPA ask for a full dashboard page in one request."""

    page_size_query_param = 'page_size'
    max_page_size = 200


@extend_schema(responses=None)
@api_view(['HEAD', 'GET'])
def api_health_check(request, version):
    response = HttpResponse()
    response['api'] = version
    return response


@extend_schema(responses=UserSerializer)
@api_view(['GET'])
def me(request, version):
    return Response(UserSerializer(request.user).data)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all().order_by('name')
    serializer_class = ProjectSerializer
    pagination_class = None


class TestViewSet(
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    serializer_class = TestSerializer
    pagination_class = TestPagination

    def get_queryset(self):
        # nulls_last matters: PostgreSQL sorts NULLs FIRST on DESC, which
        # fills the first page with never-started tests that have no data.
        queryset = Test.objects.select_related('project').order_by(
            F('started_at').desc(nulls_last=True), '-id'
        )
        params = self.request.query_params
        project_id = params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        statuses = params.getlist('status')
        if statuses:
            queryset = queryset.filter(status__in=statuses)
        if params.get('project_enabled') == 'true':
            queryset = queryset.filter(project__enabled=True)
        # Never-started tests carry no metrics; the dashboard hides them.
        if params.get('started') == 'true':
            queryset = queryset.exclude(started_at__isnull=True)
        return queryset

    def list(self, request, *args, **kwargs):
        # Batch the dashboard stats for the page instead of per-row queries.
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        tests = page if page is not None else list(queryset)
        serializer = self.get_serializer(
            tests,
            many=True,
            context={
                **self.get_serializer_context(),
                'dashboard_stats':
                    base_services.dashboard_test_stats(tests),
                'sparklines': base_services.sparklines(tests),
            },
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report(self, request, version, pk=None):
        """The full analyzer report payload (charts + aggregate table)."""
        return Response(analyzer_services.test_report_data(self.get_object()))

    @action(
        detail=True, methods=['get'],
        url_path='compare/(?P<other_id>[0-9]+)',
    )
    def compare(self, request, version, pk=None, other_id=None):
        """Comparison table + t-test highlights vs another test (0 = prev)."""
        tests = analyzer_services.resolve_compare_tests([pk, other_id])
        return Response({
            'tests': TestSerializer(
                tests, many=True, context=self.get_serializer_context()
            ).data,
            'highlights': analyzer_services.compare_highlights(tests),
            'compare_table': analyzer_services.compare_table(tests),
        })

    @action(
        detail=True, methods=['get'],
        url_path='actions/(?P<action_id>[0-9]+)',
    )
    def action_details(self, request, version, pk=None, action_id=None):
        """Per-action stats (incl. boxplot data) and errors."""
        data = analyzer_services.action_details_data(
            int(pk), int(action_id)
        )
        data['action'] = {
            'id': data['action'].id,
            'name': data['action'].name,
        }
        return Response(data)

    @extend_schema(responses=None)
    @action(detail=True, methods=['get'])
    def monitoring(self, request, version, pk=None):
        """Per-server CPU/memory series; [] when nothing was collected."""
        return Response(
            analyzer_monitoring.test_monitoring_data(self.get_object())
        )

    @extend_schema(request=None, responses=TestSerializer)
    @action(detail=True, methods=['post'])
    def stop(self, request, version, pk=None):
        """Terminate a running test (kills master + remote servers)."""
        test = self.get_object()
        stoppable = (Test.RUNNING, Test.ANALYZING, Test.SCHEDULED)
        if test.status not in stoppable:
            return Response(
                {
                    'detail': (
                        'Only a running, analyzing or scheduled test can be '
                        f'stopped (this one is {test.get_status_display()}).'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        test.terminate()
        test.refresh_from_db()
        return Response(
            self.get_serializer(test).data
        )

    @extend_schema(request=None, responses=None)
    @action(detail=True, methods=['post'])
    def publish(self, request, version, pk=None):
        """Publish this test's report page to Confluence."""
        test = self.get_object()
        if not settings.WIKI_URL:
            return Response(
                {'detail': 'Confluence is not configured on this server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        template = getattr(test.project, 'template', None)
        if template is None:
            return Response(
                {
                    'detail': (
                        'This project has no Confluence report template '
                        'configured (set one in the admin).'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            url = test.post_to_confluence(force=True)
        except Exception as error:  # network/API failures are expected here
            logger.error('Confluence publish failed: %s', error)
            return Response(
                {'detail': f'Publishing failed: {error}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({'url': url} if url else {'detail': 'published'})

    @action(detail=True, methods=['get'])
    def online(self, request, version, pk=None):
        """Live online data; refresh is throttled server-side."""
        test = self.get_object()
        online_services.refresh_online_data(test)
        return Response(
            TestOnlineSerializer(
                test, context=self.get_serializer_context()
            ).data
        )


class LoadGeneratorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        LoadGenerator.objects
        .prefetch_related('jmeter_servers')
        .annotate(jmeter_count=Count('jmeter_servers'))
        .order_by('hostname')
    )
    serializer_class = LoadGeneratorSerializer
    pagination_class = None
