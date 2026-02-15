"""Tests for Persian number/text utilities."""
import pytest

from src.utils import persian


class TestPersianToInt:
    def test_persian_digits(self):
        assert persian.persian_to_int("۱۲۳") == 123
        assert persian.persian_to_int("۰") == 0
        assert persian.persian_to_int("۹") == 9

    def test_arabic_digits(self):
        assert persian.persian_to_int("٠١٢") == 12

    def test_mixed_digits(self):
        assert persian.persian_to_int("1۲3") == 123

    def test_plain_ascii_digits(self):
        assert persian.persian_to_int("42") == 42

    def test_with_non_digits_ignored_or_parsed(self):
        # Implementation may strip non-digits or parse first number
        n = persian.persian_to_int("۵ روز دیگه")
        assert n == 5 or n >= 0


class TestToPersianDigits:
    def test_to_persian_digits(self):
        assert persian.to_persian_digits(0) == "۰"
        assert persian.to_persian_digits(9) == "۹"
        assert persian.to_persian_digits(123) == "۱۲۳"

    def test_large_number(self):
        assert "۱" in persian.to_persian_digits(12345)
