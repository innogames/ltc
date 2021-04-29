from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseForbidden
from django.utils.decorators import available_attrs


def staff_member_required(view_func=None,
                          redirect_field_name=REDIRECT_FIELD_NAME,
                          login_url='admin:login'):
    """
    Decorator for views that checks that the user is logged in and is a staff
    member, showing Forbidden response if not.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_active and user.is_staff:
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden()

        return _wrapped_view

    if view_func:
        return decorator(view_func)

    return decorator
