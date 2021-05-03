import json
from ltc.controller.models import JmeterServer, LoadGenerator
import re
import os
import hashlib

from typing import Dict
from rest_framework.exceptions import PermissionDenied
from adminapi.dataset import Query
from adminapi.parse import parse_query
from django.conf import settings
from django.db.models.query import Prefetch
from django.utils import timezone
from rest_framework import serializers
from ltc.base.models import Test, Project
from ltc.online.models import TestOnlineData

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class TestSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Test
        fields = '__all__'

    def create(self, validated_data: Dict) -> Test:
        project = validated_data.get('project')
        project, _ = Project.objects.get_or_create(name=project)
        test = Test(project=Project)
        return test


class JmeterServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = JmeterServer
        fields = '__all__'


class LoadGeneratorSerializer(serializers.ModelSerializer):
    jmeter_servers = JmeterServerSerializer(read_only=True, many=True)

    class Meta:
        model = LoadGenerator
        fields = '__all__'


class OnlineDataSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(required=False)

    class Meta:
        model = TestOnlineData
        fields = '__all__'

class TestSerializer(serializers.ModelSerializer):
    online_data = OnlineDataSerializer(required=False, many=True)
    project = ProjectSerializer(read_only=True)
    class Meta:
        model = Test
        fields = (
            'id',
            'name',
            'project',
            'status',
            'duration',
            'online_data',
            'started_at',
        )

    @staticmethod
    def setup_eager_loading(queryset):
        """Perform necessary eager loading of data.
        """
        queryset = queryset.prefetch_related(
            'online_data'
        )
        return queryset