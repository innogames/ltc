from rest_framework import serializers

from ltc.base import services as base_services
from ltc.base.models import Project, Test
from ltc.controller.models import JmeterServer, LoadGenerator
from ltc.online.models import TestOnlineData


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name', 'enabled')


class OnlineDataSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(required=False)

    class Meta:
        model = TestOnlineData
        fields = ('id', 'name', 'data')


class TestSerializer(serializers.ModelSerializer):
    """Test list/detail with dashboard stats (see ltc.base.services)."""

    project = ProjectSerializer(read_only=True)
    project_name = serializers.CharField(write_only=True, required=False)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = (
            'id',
            'name',
            'project',
            'project_name',
            'status',
            'threads',
            'duration',
            'started_at',
            'finished_at',
            'stats',
        )
        read_only_fields = (
            'id', 'project', 'started_at', 'finished_at', 'stats',
        )

    def get_stats(self, obj) -> dict:
        stats = self.context.get('dashboard_stats')
        if stats is None:
            stats = base_services.dashboard_test_stats([obj])
        row = stats.get(obj.id)
        if row is None:
            return None
        prev_mean = row['prev_test_data'].get('mean')
        mean = row['test_data'].get('mean')
        mean_diff_percent = None
        if mean is not None and prev_mean:
            mean_diff_percent = round((mean - prev_mean) * 100 / prev_mean, 1)
        return {
            'mean': mean,
            'count': row['test_data'].get('count_sum'),
            'errors': row['test_data'].get('errors_sum'),
            'success_requests': round(row['success_requests'], 2),
            'success_level': row['result'],
            'prev_test_id': row['prev_test_id'],
            'prev_test_mean': prev_mean,
            'mean_diff_percent': mean_diff_percent,
        }

    def create(self, validated_data):
        project_name = validated_data.pop('project_name', None)
        project = None
        if project_name:
            project, _ = Project.objects.get_or_create(name=project_name)
        return Test.objects.create(project=project, **validated_data)


class TestOnlineSerializer(serializers.ModelSerializer):
    """Test with live online data — polled by the Online page."""

    online_data = OnlineDataSerializer(read_only=True, many=True)
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Test
        fields = (
            'id',
            'name',
            'project',
            'status',
            'duration',
            'started_at',
            'online_data',
        )


class JmeterServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = JmeterServer
        fields = (
            'id', 'test', 'pid', 'port', 'jmeter_path', 'threads',
        )


class LoadGeneratorSerializer(serializers.ModelSerializer):
    jmeter_servers = JmeterServerSerializer(read_only=True, many=True)

    class Meta:
        model = LoadGenerator
        fields = (
            'id', 'hostname', 'num_cpu', 'memory', 'memory_free',
            'la_1', 'la_5', 'la_15', 'active', 'jmeter_servers',
        )


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    is_staff = serializers.BooleanField()
