import datetime
from django import template

register = template.Library()


@register.simple_tag()
def get_percentage(a1, a2, *args, **kwargs):
    try:
        return round(100 * a1 / a2, 1)
    except (TypeError, ZeroDivisionError) as e:
        return 0


@register.simple_tag()
def get_percentage_abs(a1, a2, *args, **kwargs):
    try:
        p = 0
        if a2 > a1:
            p = (a2 - a1) / a1 * 100
        elif a2 < a1:
            p = (a1 - a2) / a2 * 100
        return abs(round(p, 1))
    except (TypeError, ZeroDivisionError) as e:
        return 0


@register.simple_tag()
def get_percentage_rel(a1, a2, *args, **kwargs):
    try:
        return round(100 - 100 * a1 / a2, 1)
    except (TypeError, ZeroDivisionError) as e:
        return 0


@register.simple_tag()
def subtract(a1, a2, *args, **kwargs):
    return a1 - a2


@register.simple_tag()
def print_timestamp(timestamp, *args, **kwargs):
    return datetime.datetime.fromtimestamp(timestamp / 1000)


@register.simple_tag()
def seconds_to_time(seconds, *args, **kwargs):
    return str(datetime.timedelta(seconds=int(seconds)))
