from httpkit.builders.request_header import RequestHeaderBuilder


def test_empty_build() -> None:
    result = RequestHeaderBuilder().build()
    expected: dict[str, str] = {}

    assert result == expected


def test_add_content_type_default_value() -> None:
    result = RequestHeaderBuilder().add_content_type().build()
    expected = {"Content-Type": "application/json"}

    assert result == expected


def test_add_content_type_custom_value() -> None:
    value = "application/xml"
    result = RequestHeaderBuilder().add_content_type(content_type=value).build()
    expected = {"Content-Type": value}

    assert result == expected


def test_add_accept_default_value() -> None:
    result = RequestHeaderBuilder().add_accept().build()
    expected = {"Accept": "application/json"}

    assert result == expected


def test_add_accept_custom_value() -> None:
    value = "application/xml"
    result = RequestHeaderBuilder().add_accept(accept=value).build()
    expected = {"Accept": value}

    assert result == expected


def test_add_authorization() -> None:
    result = (
        RequestHeaderBuilder().add_authorization(authorization="Bearer token").build()
    )
    expected = {"Authorization": "Bearer token"}

    assert result == expected


def test_add_custom_field() -> None:
    result = RequestHeaderBuilder().add_custom_field(key="Custom", value="val").build()
    expected = {"Custom": "val"}

    assert result == expected


def test_add_user_agent() -> None:
    result = RequestHeaderBuilder().add_user_agent(user_agent="mozilla").build()
    expected = {"User-Agent": "mozilla"}

    assert result == expected


def test_add_multiple() -> None:
    result = (
        RequestHeaderBuilder()
        .add_content_type()
        .add_accept()
        .add_authorization(authorization="Bearer token")
        .build()
    )
    expected = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer token",
    }

    assert result == expected
