from http import HTTPMethod

import pytest

from saint_elmo_backend.httpkit.exceptions import (
    HttpkitConnectionError,
    HttpkitStatusError,
    HttpkitTimeoutError,
    HttpkitTransportError,
    HttpkitValidationError,
)
from saint_elmo_backend.httpkit.tests.conftest import MakeClient
from saint_elmo_backend.httpkit.tests.fakes import FakeResponse, Product

# Header merging


def test_use_client_headers_when_no_custom_headers_are_passed(
    make_client: MakeClient,
) -> None:
    """
    Test if transport layer received only the header fields specified on the client
    without adding anything from the request.
    """

    client, transport = make_client(
        response=FakeResponse(), headers={"Content-Type": "text/html", "Accept": "*"}
    )
    _ = client.request(url="/products")

    assert transport.received is not None

    assert transport.received.headers == {"Content-Type": "text/html", "Accept": "*"}


def test_request_headers_take_precedence_over_client_headers(
    make_client: MakeClient,
) -> None:
    """
    Test if transport layer received only the header fields specified on the client
    without adding anything from the request.
    """

    client, transport = make_client(
        response=FakeResponse(),
        headers={
            "Content-Type": "text/html",
            "Accept": "*",
        },
    )

    _ = client.request(
        url="/products",
        headers={"Content-Type": "application/json", "Authorization": "Bearer Token"},
    )

    assert transport.received is not None

    assert transport.received.headers == {
        "Content-Type": "application/json",
        "Accept": "*",
        "Authorization": "Bearer Token",
    }


# Request construction


def test_all_request_arguments_are_passed_to_the_transport_layer(
    make_client: MakeClient,
):
    """
    All request arguments (method, url, headers, params, json, content, and timeout) are passed to the transport layer unchanged.
    """

    client, transport = make_client(
        response=FakeResponse(),
    )

    _ = client.request(
        url="/products",
        method=HTTPMethod.POST,
        headers={"x-Custom": "Testing"},
        params={"first_name": "joe", "last_name": "doe"},
        json={"first_name": "joe", "last_name": "doe"},
        timeout=15,
    )

    assert transport.received is not None

    assert transport.received.url == "/products"
    assert transport.received.method == HTTPMethod.POST
    assert transport.received.headers == {"x-Custom": "Testing"}
    assert transport.received.params == {"first_name": "joe", "last_name": "doe"}
    assert transport.received.json == {"first_name": "joe", "last_name": "doe"}
    assert transport.received.timeout == 15


def test_get_method_is_a_default_request_method(
    make_client: MakeClient,
):
    """
    Make sure that GET is a default HTTP method when no method is provided.
    """

    client, transport = make_client(
        response=FakeResponse(),
    )

    _ = client.request(
        url="/products",
        headers={"x-Custom": "Testing"},
        params={"first_name": "joe", "last_name": "doe"},
        json={"first_name": "joe", "last_name": "doe"},
        timeout=15,
    )

    assert transport.received is not None

    assert transport.received.url == "/products"
    assert transport.received.method == HTTPMethod.GET
    assert transport.received.headers == {"x-Custom": "Testing"}
    assert transport.received.params == {"first_name": "joe", "last_name": "doe"}
    assert transport.received.json == {"first_name": "joe", "last_name": "doe"}
    assert transport.received.timeout == 15


# Status Handling


def test_receiving_200_does_not_raise(make_client: MakeClient):
    """
    Receiving 200 does not raise an error.
    """

    client, _ = make_client(
        response=FakeResponse(),
    )

    response = client.request(url="/products")

    assert response.status_code == 200


@pytest.mark.parametrize("status", [400, 401, 404, 422, 500, 503])
def test_receiving_non_200_raises_status_error(make_client: MakeClient, status: int):
    """
    Received non-2xx raises status error.
    """
    client, _ = make_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = client.request(url="/products")

    assert err.value.status_code == status


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_status_codes(make_client: MakeClient, status: int):
    """
    Certain status codes are retryable
    """
    client, _ = make_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = client.request(url="/products")

    assert err.value.is_retryable() is True


@pytest.mark.parametrize("status", [400, 401, 404, 422])
def test_non_retryable_status_codes(make_client: MakeClient, status: int):
    """
    Certain status codes are non-retryable
    """
    client, _ = make_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = client.request(url="/products")

    assert err.value.is_retryable() is False


def test_status_error_carries_context(make_client: MakeClient):
    client, _ = make_client(response=FakeResponse(status=400, body="{'error': 'nope'}"))
    with pytest.raises(HttpkitStatusError) as err:
        _ = client.request(url="/products")

    e = err.value
    assert (e.status_code, e.error_body, e.method, e.url) == (
        400,
        "{'error': 'nope'}",
        HTTPMethod.GET,
        "/products",
    )


# Payload — success paths


def test_payload_is_validated_into_response_model(make_client: MakeClient):
    """
    With a response_model, a valid JSON body is validated into a model instance.
    """
    client, _ = make_client(response=FakeResponse(status=200, body='{"id": 1, "name": "Widget"}'))

    response = client.request(url="/products", response_model=Product)

    assert isinstance(response.payload, Product)
    assert response.payload == Product(id=1, name="Widget")


def test_payload_without_response_model_is_decoded_json(make_client: MakeClient):
    """
    Without a response_model, a JSON body is decoded and returned as-is.
    """
    client, _ = make_client(response=FakeResponse(status=200, body='{"first_name": "joe"}'))

    response = client.request(url="/products")

    assert response.payload == {"first_name": "joe"}


def test_empty_body_without_response_model_is_none(make_client: MakeClient):
    """
    Without a response_model, an empty body yields a None payload.
    """
    client, _ = make_client(response=FakeResponse(status=200, body=""))

    response = client.request(url="/products")

    assert response.payload is None


# Payload — validation / decode errors


def test_response_model_with_mismatched_body_raises_validation_error(
    make_client: MakeClient,
):
    """
    With a response_model, a JSON body that fails validation raises a validation error.
    """
    client, _ = make_client(
        response=FakeResponse(status=200, body='{"name": "Widget"}')  # missing id
    )

    with pytest.raises(HttpkitValidationError):
        _ = client.request(url="/products", response_model=Product)


def test_response_model_with_non_json_body_raises_validation_error(
    make_client: MakeClient,
):
    """
    With a response_model, a non-JSON body raises a validation error.
    """
    client, _ = make_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError):
        _ = client.request(url="/products", response_model=Product)


def test_non_json_body_without_response_model_raises_validation_error(
    make_client: MakeClient,
):
    """
    Without a response_model, a non-JSON body cannot be decoded and raises a validation error.
    """
    client, _ = make_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError):
        _ = client.request(url="/products")


def test_validation_error_carries_context(make_client: MakeClient):
    """
    A validation error carries the request context (status code, method, url).
    """
    client, _ = make_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError) as err:
        _ = client.request(url="/products", method=HTTPMethod.POST)

    e = err.value
    assert (e.status_code, e.method, e.url) == (200, HTTPMethod.POST, "/products")


# Transport errors


@pytest.mark.parametrize(
    "raised",
    [
        HttpkitTimeoutError(message="boom", method=HTTPMethod.GET, url="/products"),
        HttpkitConnectionError(message="boom", method=HTTPMethod.GET, url="/products"),
        HttpkitTransportError(message="boom", method=HTTPMethod.GET, url="/products"),
    ],
)
def test_transport_errors_propagate_untouched(
    make_client: MakeClient, raised: HttpkitTransportError
):
    """
    Transport-layer errors bubble up unchanged, with retryability preserved.
    """
    client, _ = make_client(raises=raised)

    with pytest.raises(HttpkitTransportError) as err:
        _ = client.request(url="/products")

    assert err.value is raised
    assert err.value.is_retryable() is raised.is_retryable()


# Response metadata


def test_response_surfaces_status_code_and_headers(make_client: MakeClient):
    """
    The status code and headers from the raw response are surfaced on the Response.
    """
    client, _ = make_client(
        response=FakeResponse(status=200, body='{"a": 1}', headers={"X-Trace": "abc"})
    )

    response = client.request(url="/products")

    assert response.status_code == 200
    assert response.headers == {"X-Trace": "abc"}
    assert response.payload == {"a": 1}
