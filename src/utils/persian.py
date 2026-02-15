"""Persian number/text utilities."""
import re

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def persian_to_int(s: str) -> int:
    """Convert Persian/Arabic digits in string to integer."""
    s = str(s).strip()
    table = str.maketrans(PERSIAN_DIGITS + ARABIC_DIGITS, "0123456789" * 2)
    cleaned = ""
    for c in s:
        if c in PERSIAN_DIGITS or c in ARABIC_DIGITS:
            cleaned += c.translate(table)
        elif c.isdigit():
            cleaned += c
        elif cleaned:
            break
    return int(cleaned) if cleaned else 0


def to_persian_digits(n: int) -> str:
    """Convert integer to Persian digit string."""
    table = str.maketrans("0123456789", PERSIAN_DIGITS)
    return str(n).translate(table)
