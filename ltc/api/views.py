from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

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

    def get_queryset(self):
        queryset = Test.objects.select_related('project').order_by(
            '-started_at'
        )
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        statuses = self.request.query_params.getlist('status')
        if statuses:
            queryset = queryset.filter(status__in=statuses)
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
    queryset = LoadGenerator.objects.prefetch_related(
        'jmeter_servers'
    ).order_by('hostname')
    serializer_class = LoadGeneratorSerializer
    pagination_class = None
