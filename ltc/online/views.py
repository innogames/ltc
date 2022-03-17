import fnmatch
import logging
import os
from django.contrib.auth.decorators import login_required
from django.db.models import FloatField, Sum
from django.db.models.expressions import F, RawSQL
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from ltc.base.models import Project, Test


logger = logging.getLogger('django')

# Create your views here.

@login_required
def index(request):
    context = {}
    context['tests'] = Test.objects.filter(status=Test.RUNNING)
    return render(request, 'online/index.html', context)
