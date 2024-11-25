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

@register.filter
def divide_by_60(value):
    if value is not None:
        return round(value / 60, 2)
    return None

@register.filter
def get_item_for_stage(summary_list, stage):
    """
    Retrieve the dictionary for the specific stage from the summary list.
    The summary_list should be a list of dictionaries, each containing `stage`, `count`, and `percentage`.
    """
    if not summary_list or not isinstance(summary_list, list):
        return None  # Return None if the input is not valid
    for item in summary_list:
        if item.get('stage') == stage:
            return item  # Return the dictionary for the matching stage
    return None  # Return None if no match is found

@register.filter
def format_number(value):
    try:
        value = float(value)
        return f"{value:,.2f}"  # Adds commas as thousand separators and keeps two decimal places
    except (ValueError, TypeError):
        return value  # Return original value if it's not a number
