from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value"""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value

@register.filter
def split(value, arg):
    """Splits the value by arg and returns the list"""
    return value.split(arg)