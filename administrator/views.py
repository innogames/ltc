from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from administrator.models import JMeterProfile


def administrator_page(request):
    jds = JMeterProfile.objects.values()
    return render(request, 'administrator_page.html', {
        'jds': jds,
    })


def new_jd_page(request):
    new_jd = JMeterProfile()
    new_jd.save()
    return render(request, 'new_jd.html', {
        'jd': new_jd,
    })


def delete_jd(request, jd_id):
    jd = JMeterProfile.objects.get(id=jd_id)
    jd.delete()
    response = {
        "message": {
            "text": "JMeter distro deleted",
            "type": "warning",
            "msg_params": {
                "id": jd_id
            }
        }
    }
    return JsonResponse(response, safe=False)


def create_jd(request, jd_id):
    jd = JMeterProfile.objects.get(id=jd_id)
    response = {}
    if request.method == 'POST':
        name = request.POST.get('name', '')
        path = request.POST.get('path', '')
        version = request.POST.get('version', '')
        jvm_args_main = request.POST.get('jvm_args_main', '')
        jvm_args_jris = request.POST.get('jvm_args_jris', '')
        jd.name = name
        jd.path = path
        jd.version = version
        jd.jvm_args_main = jvm_args_main
        jd.jvm_args_jris = jvm_args_jris
        jd.save()
        response = {
            "message": {
                "text": "JMeter distro was added",
                "type": "info",
                "msg_params": {
                    "id": jd_id
                }
            }
        }
    return JsonResponse(response, safe=False)
