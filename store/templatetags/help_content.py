from django import template
register = template.Library()
@register.filter
def help_sections(value):
    result=[]
    for paragraph in value.replace('\r\n','\n').split('\n\n'):
        heading, sep, body=paragraph.partition('\n')
        if paragraph.strip():
            result.append({'heading': heading if sep else '', 'body': body if sep else paragraph})
    return result
