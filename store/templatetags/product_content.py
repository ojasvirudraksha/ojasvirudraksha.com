from django import template

register = template.Library()
HEADINGS = {'Product details', 'Traditional use', 'Care guidance', 'Please note', 'Sample details'}


@register.filter
def description_sections(value):
    """Recognize editorial headings while leaving merchant text safely escaped."""
    sections = []
    for paragraph in (value or '').replace('\r\n', '\n').split('\n\n'):
        heading, separator, body = paragraph.partition('\n')
        if separator and heading in HEADINGS:
            sections.append({'heading': heading, 'body': body})
        elif paragraph.strip():
            sections.append({'heading': '', 'body': paragraph})
    return sections
