from app.intents import IntentDetector, Intent

detector = IntentDetector()


def test_greeting_intent():
    assert detector.detect("hello") == Intent.GREETING
    assert detector.detect("hi there") == Intent.GREETING


def test_farewell_intent():
    assert detector.detect("bye") == Intent.FAREWELL
    assert detector.detect("ok goodbye") == Intent.FAREWELL


def test_calculation_intent():
    assert detector.detect("what is 12 * 7") == Intent.CALCULATION
    assert detector.detect("5 + 5") == Intent.CALCULATION


def test_datetime_intent():
    assert detector.detect("what is today's date") == Intent.DATETIME
    assert detector.detect("what time is it") == Intent.DATETIME


def test_file_question_intent():
    assert detector.detect("what does the document say about refunds") == Intent.FILE_QUESTION


def test_general_intent_fallback():
    assert detector.detect("tell me a joke") == Intent.GENERAL


def test_extract_expression():
    assert detector.extract_expression("what is 3 + 4") == "3 + 4"
    assert detector.extract_expression("no numbers here") is None
