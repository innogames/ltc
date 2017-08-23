from django import template

register = template.Library()

@register.simple_tag()
def get_percentage(a1, a2, *args, **kwargs):
	return round(100 * a1 / a2, 1)