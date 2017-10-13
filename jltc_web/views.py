from django.shortcuts import render
from django.views.decorators.cache import never_cache
# Create your views here.
from django.views.generic import TemplateView

from administrator.models import User


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
        })