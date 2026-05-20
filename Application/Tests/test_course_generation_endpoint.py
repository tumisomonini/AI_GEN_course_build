import pytest


def test_generate_endpoint_imports():
    # Lightweight import test: ensures route wiring works.
    from Application.API.Endpoints.courses_generate import GenerateCourseRequest  # noqa: F401


def test_generate_request_validation():
    from Application.API.Endpoints.courses_generate import GenerateCourseRequest

    req = GenerateCourseRequest(title="Intro to AI", level="beginner", duration_months=3)
    assert req.title == "Intro to AI"

    with pytest.raises(Exception):
        GenerateCourseRequest(title="Bad", level="wrong_level", duration_months=3)

