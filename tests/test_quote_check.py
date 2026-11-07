from src.tools import unsupported_quotes

REAL = "We will pay this benefit if your trip is delayed for 6 continuous hours or more"


def test_real_quote_passes():
    assert unsupported_quotes(f'The policy says "{REAL}".', "fwd") == []


def test_edited_number_is_caught():
    fake = REAL.replace("6", "3")
    assert unsupported_quotes(f'The endorsement states: “{fake}.”', "fwd") == [fake + "."]


def test_short_quotes_and_ellipsis_pieces():
    assert unsupported_quotes('It says "typhoon" and "We will pay this benefit ... 6 continuous hours or more".', "fwd") == []
