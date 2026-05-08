from fixture_app.greetings import greet


def test_greet_adds_punctuation() -> None:
    assert greet("Ada") == "Hello, Ada!"
