
"""
Built-in tools NEXA can call directly, without any LLM:
  - safe_calculate(): arithmetic evaluator using the `ast` module
    (NEVER uses eval()/exec()).
  - get_datetime_info(): answers date/time/day questions using
    India Standard Time (IST).
"""

import ast
import operator
import datetime

from .logger import get_logger

log = get_logger(__name__)

# India Standard Time (IST) = UTC + 5 hours 30 minutes.
# India does not use daylight saving time.
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


# Whitelisted operators only - anything else raises ValueError.
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_MAX_POWER_EXPONENT = 1000  # guard against ** based DoS


class CalculatorError(ValueError):
    pass


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalculatorError("Only numeric constants are allowed.")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)

        if op_type not in _ALLOWED_OPERATORS:
            raise CalculatorError(
                f"Operator {op_type.__name__} is not allowed."
            )

        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if op_type is ast.Pow and abs(right) > _MAX_POWER_EXPONENT:
            raise CalculatorError("Exponent too large.")

        return _ALLOWED_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)

        if op_type not in _ALLOWED_OPERATORS:
            raise CalculatorError(
                f"Operator {op_type.__name__} is not allowed."
            )

        return _ALLOWED_OPERATORS[op_type](
            _eval_node(node.operand)
        )

    raise CalculatorError(
        f"Unsupported expression: {type(node).__name__}"
    )


def safe_calculate(expression: str) -> float:
    """Safely evaluate a basic arithmetic expression.

    Supports + - * / // % ** and parentheses.
    Raises CalculatorError on anything else (names, calls, attribute
    access, comprehensions, etc.) so this can never be used to execute
    arbitrary code, unlike eval().
    """
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError(
            f"Invalid expression: {exc}"
        ) from exc

    try:
        result = _eval_node(parsed.body)
    except ZeroDivisionError as exc:
        raise CalculatorError(
            "Division by zero."
        ) from exc

    return result


def get_datetime_info(query: str) -> str:
    """Answer simple date/time questions using India Standard Time."""

    # Always use IST, regardless of the computer/server timezone.
    now = datetime.datetime.now(IST)

    q = query.lower()

    if "day" in q and "date" not in q and "time" not in q:
        return f"Today is {now.strftime('%A')}."

    if "date" in q:
        return f"Today's date is {now.strftime('%d %B %Y')}."

    if "time" in q:
        return f"The current time is {now.strftime('%I:%M %p')}."

    if "year" in q:
        return f"The current year is {now.year}."

    if "month" in q:
        return f"The current month is {now.strftime('%B')}."

    return (
        f"Right now it's "
        f"{now.strftime('%A, %d %B %Y, %I:%M %p')}."
    )