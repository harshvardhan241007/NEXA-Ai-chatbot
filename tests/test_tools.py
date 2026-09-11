import pytest
from app.tools import safe_calculate, CalculatorError, get_datetime_info


def test_basic_addition():
    assert safe_calculate("2 + 2") == 4


def test_operator_precedence():
    assert safe_calculate("2 + 3 * 4") == 14


def test_division():
    assert safe_calculate("10 / 2") == 5.0


def test_division_by_zero_raises():
    with pytest.raises(CalculatorError):
        safe_calculate("1 / 0")


def test_power():
    assert safe_calculate("2 ** 5") == 32


def test_rejects_function_calls():
    """Must NOT behave like eval() - no code execution allowed."""
    with pytest.raises(CalculatorError):
        safe_calculate("__import__('os').system('echo pwned')")


def test_rejects_names():
    with pytest.raises(CalculatorError):
        safe_calculate("open('/etc/passwd')")


def test_rejects_huge_exponent():
    with pytest.raises(CalculatorError):
        safe_calculate("2 ** 999999")


def test_datetime_time_query():
    reply = get_datetime_info("what time is it")
    assert "time" in reply.lower()


def test_datetime_date_query():
    reply = get_datetime_info("what is the date today")
    assert "date" in reply.lower()
