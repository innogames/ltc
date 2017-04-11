from django.shortcuts import render
from django.views.decorators.cache import never_cache
# Create your views here.
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    @never_cache
    def get(self, request, **kwargs):
        return render(request, 'index.html', context=None)