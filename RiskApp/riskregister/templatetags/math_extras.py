from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def multiply(a, b):
    """Multiply two values, converting strings to integers if needed."""
    try:
        a_int = int(a)
        b_int = int(b)
        return a_int * b_int
    except (ValueError, TypeError):
        return 0

@register.filter
def abs_value(value):
    """Return the absolute value of a number."""
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key.
    
    Usage: {{ my_dict|get_item:some_key }}
    """
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def format_currency(value, currency_code='USD'):
    """Format a numeric value as currency with appropriate symbol and 2 decimal places.
    
    Usage: {{ value|format_currency:"USD" }}
           {{ value|format_currency:"ZWL" }}
    """
    try:
        amount = Decimal(str(value))
        
        currency_symbols = {
            'USD': '$',
            'ZWL': 'ZWL$',
            'EUR': '€',
            'GBP': '£',
            'ZAR': 'R',
            'BWP': 'P',
        }
        
        symbol = currency_symbols.get(currency_code.upper(), currency_code)
        
        # Format with comma separators and 2 decimal places
        formatted = f"{amount:,.2f}"
        
        return f"{symbol}{formatted}"
    except (ValueError, TypeError, InvalidOperation):
        return f"{currency_code}0.00"

@register.filter
def format_number(value, decimals=2):
    """Format a numeric value with specified decimal places.
    
    Usage: {{ value|format_number:2 }}
    """
    try:
        num = Decimal(str(value))
        format_str = f"{{:,.{int(decimals)}f}}"
        return format_str.format(num)
    except (ValueError, TypeError):
        return "0.00"

@register.filter
def variance_sign(value):
    """Add + or - sign to variance values.
    
    Usage: {{ variance|variance_sign }}
    """
    try:
        num = Decimal(str(value))
        if num > 0:
            return f"+{num:,.2f}"
        else:
            return f"{num:,.2f}"
    except (ValueError, TypeError):
        return "0.00"

# Alias for multiply filter
@register.filter
def mul(a, b):
    """Alias for multiply filter."""
    return multiply(a, b)