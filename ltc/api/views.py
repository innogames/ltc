from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse

@api_view(['GET'])
def api_root(request, version):
    return Response({
        'events': reverse(
            'api.event-all', request=request, kwargs={'version': version}
        ),
        'tickets': reverse(
            'api.ticket-all', request=request, kwargs={'version': version}
        ),
    })


# Create your views here.
@api_view(['HEAD', 'GET'])
def api_health_check(request, version):
    response = HttpResponse()
    response['api'] = version
    return response
