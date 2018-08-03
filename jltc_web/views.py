import zipfile
import os
import logging
from django.shortcuts import render
from django.views.decorators.cache import never_cache
# Create your views here.
from django.views.generic import TemplateView
from os.path import basename
from administrator.models import User, Configuration
from analyzer.models import Project
from django.views.static import serve

logger = logging.getLogger(__name__)

def zipDir(dirPath, zipPath):
    zipf = zipfile.ZipFile(zipPath , mode='w')
    lenDirPath = len(dirPath)
    for root, _ , files in os.walk(dirPath):
        for file in files:
            filePath = os.path.join(root, file)
            zipf.write(filePath , filePath[lenDirPath :] )
    zipf.close()

class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        LoginAuth_jltom = request.COOKIES.get('LoginAuth_jltc')
        if LoginAuth_jltom is None:
            login_auth = "unknown_user"
        else:
            login_auth = request.COOKIES.get('LoginAuth_jltc').split(':')[0]
        if not User.objects.filter(login=login_auth).exists():
            u = User(login=login_auth)
            u.save()
            user_id = u.id
        else:
            u = User.objects.get(login=login_auth)
            user_id = u.id
        return render(request, 'index.html', {
            'user': u,
            'projects': Project.objects.all()
        })


def get_jmeter(request):
    jmeter_path = Configuration.objects.get(name='jmeter_path').value

    jmeter_zip_path = '/tmp/jmeter.zip'
    logger.info("Packing Jmeter distributive.")
    if not os.path.exists(jmeter_zip_path):
        zipDir(jmeter_path, jmeter_zip_path)
    return serve(request,
                 os.path.basename(jmeter_zip_path),
                 os.path.dirname(jmeter_zip_path))
