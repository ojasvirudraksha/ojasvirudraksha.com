from django import template
from store.currency import market, format_money
register = template.Library()

@register.simple_tag(takes_context=True)
def money(context, value, converted=False):
    return format_money(value, market(context['request']), converted=converted)
