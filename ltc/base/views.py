import logging
import os

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

logger = logging.getLogger('django')


def spa(request, path=''):
    """
    Serve the built React SPA (frontend/dist/index.html) for every
    client-side route; assets come from staticfiles. See
    .claude/docs/frontend.md.
    """
    index = os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html')
    if not os.path.exists(index):
        return HttpResponse(
            'Frontend build missing — run `make frontend-build`.',
            status=503,
        )
    return render(request, 'index.html')
