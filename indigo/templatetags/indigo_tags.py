from django import template

register = template.Library()


@register.filter
def simplify_field_title(value):
    """
    A simple filter to simplify field titles
    """
    try:
        start = value.find(" - ")
        end = value.rfind(" - ")

        if start != -1 or end != -1:
            if start < end:
                value = value[start + 2 : end]
            else:
                value = value[start + 2 :]
    except:
        pass

    return value
