from django import template

register = template.Library()

@register.filter
def currency(value):
    """Format decimal to Brazilian Real format"""
    if value is None:
        return 'R$ 0,00'
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return value
