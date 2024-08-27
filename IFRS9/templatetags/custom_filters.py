from django import template

register = template.Library()

@register.filter
def get_attribute(value, attr_name):
    return getattr(value, attr_name, None)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_item(dictionary, key):
    """Safely get an item from a dictionary."""
    if dictionary is None:
        return None
    return dictionary.get(key)