from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from administrator.models import JMeterProfile, SSHKey

def administrator_page(request):
    jds = JMeterProfile.objects.values()
    ssh_keys = SSHKey.objects.values()
    return render(request, 'administrator_page.html', {
        'jds': jds,
        'ssh_keys':ssh_keys
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


def new_ssh_key_page(request):
    new_ssh_key = SSHKey()
    new_ssh_key.save()
    return render(request, 'new_ssh_key.html', {
        'ssh_key': new_ssh_key,
    })


def delete_ssh_key(request, ssh_key_id):
    ssh_key = SSHKey.objects.get(id=ssh_key_id)
    ssh_key.delete()
    response = {
        "message": {
            "text": "SSH-key was deleted",
            "type": "warning",
            "msg_params": {
                "id": ssh_key_id
            }
        }
    }
    return JsonResponse(response, safe=False)


def create_ssh_key(request, ssh_key_id):
    ssh_key = SSHKey.objects.get(id=ssh_key_id)
    response = {}
    if request.method == 'POST':
        path = request.POST.get('path', '')
        description = request.POST.get('description', '')
        ssh_key.path = path
        ssh_key.description = description
        ssh_key.save()
        response = {
            "message": {
                "text": "SSH-key was added",
                "type": "info",
                "msg_params": {
                    "id": ssh_key_id
                }
            }
        }
    return JsonResponse(response, safe=False)
