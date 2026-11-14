from http import HTTPMethod

import pytest

from saint_elmo_backend.httpkit.exceptions import (
    HttpkitConnectionError,
    HttpkitStatusError,
    HttpkitTimeoutError,
    HttpkitTransportError,
    HttpkitValidationError,
)
from saint_elmo_backend.httpkit.tests.conftest import MakeAsyncClient
from saint_elmo_backend.httpkit.tests.fakes import FakeResponse, Product

# Header merging


async def test_use_client_headers_when_no_custom_headers_are_passed(
    make_async_client: MakeAsyncClient,
) -> None:
    """
    Test if transport layer received only the header fields specified on the client
    without adding anything from the request.
    """

    client, transport = make_async_client(
        response=FakeResponse(), headers={"Content-Type": "text/html", "Accept": "*"}
    )
    _ = await client.arequest(url="/products")

    assert transport.received is not None

    assert transport.received.headers == {"Content-Type": "text/html", "Accept": "*"}


async def test_request_headers_take_precedence_over_client_headers(
    make_async_client: MakeAsyncClient,
) -> None:
    """
    Test if transport layer received only the header fields specified on the client
    without adding anything from the request.
    """

    client, transport = make_async_client(
        response=FakeResponse(),
        headers={
            "Content-Type": "text/html",
            "Accept": "*",
        },
    )

    _ = await client.arequest(
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


async def test_all_request_arguments_are_passed_to_the_transport_layer(
    make_async_client: MakeAsyncClient,
):
    """
    All request arguments (method, url, headers, params, json, content, and timeout) are passed to the transport layer unchanged.
    """

    client, transport = make_async_client(
        response=FakeResponse(),
    )

    _ = await client.arequest(
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


async def test_get_method_is_a_default_request_method(
    make_async_client: MakeAsyncClient,
):
    """
    Make sure that GET is a default HTTP method when no method is provided.
    """

    client, transport = make_async_client(
        response=FakeResponse(),
    )

    _ = await client.arequest(
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


async def test_receiving_200_does_not_raise(make_async_client: MakeAsyncClient):
    """
    Receiving 200 does not raise an error.
    """

    client, _ = make_async_client(
        response=FakeResponse(),
    )

    response = await client.arequest(url="/products")

    assert response.status_code == 200


@pytest.mark.parametrize("status", [400, 401, 404, 422, 500, 503])
async def test_receiving_non_200_raises_status_error(
    make_async_client: MakeAsyncClient, status: int
):
    """
    Received non-2xx raises status error.
    """
    client, _ = make_async_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = await client.arequest(url="/products")

    assert err.value.status_code == status


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_retryable_status_codes(make_async_client: MakeAsyncClient, status: int):
    """
    Certain status codes are retryable
    """
    client, _ = make_async_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = await client.arequest(url="/products")

    assert err.value.is_retryable() is True


@pytest.mark.parametrize("status", [400, 401, 404, 422])
async def test_non_retryable_status_codes(make_async_client: MakeAsyncClient, status: int):
    """
    Certain status codes are non-retryable
    """
    client, _ = make_async_client(response=FakeResponse(status=status))
    with pytest.raises(HttpkitStatusError) as err:
        _ = await client.arequest(url="/products")

    assert err.value.is_retryable() is False


async def test_status_error_carries_context(make_async_client: MakeAsyncClient):
    client, _ = make_async_client(response=FakeResponse(status=400, body="{'error': 'nope'}"))
    with pytest.raises(HttpkitStatusError) as err:
        _ = await client.arequest(url="/products")

    e = err.value
    assert (e.status_code, e.error_body, e.method, e.url) == (
        400,
        "{'error': 'nope'}",
        HTTPMethod.GET,
        "/products",
    )


# Payload — success paths


async def test_payload_is_validated_into_response_model(
    make_async_client: MakeAsyncClient,
):
    """
    With a response_model, a valid JSON body is validated into a model instance.
    """
    client, _ = make_async_client(
        response=FakeResponse(status=200, body='{"id": 1, "name": "Widget"}')
    )

    response = await client.arequest(url="/products", response_model=Product)

    assert isinstance(response.payload, Product)
    assert response.payload == Product(id=1, name="Widget")


async def test_payload_without_response_model_is_decoded_json(
    make_async_client: MakeAsyncClient,
):
    """
    Without a response_model, a JSON body is decoded and returned as-is.
    """
    client, _ = make_async_client(response=FakeResponse(status=200, body='{"first_name": "joe"}'))

    response = await client.arequest(url="/products")

    assert response.payload == {"first_name": "joe"}


async def test_empty_body_without_response_model_is_none(
    make_async_client: MakeAsyncClient,
):
    """
    Without a response_model, an empty body yields a None payload.
    """
    client, _ = make_async_client(response=FakeResponse(status=200, body=""))

    response = await client.arequest(url="/products")

    assert response.payload is None


# Payload — validation / decode errors


async def test_response_model_with_mismatched_body_raises_validation_error(
    make_async_client: MakeAsyncClient,
):
    """
    With a response_model, a JSON body that fails validation raises a validation error.
    """
    client, _ = make_async_client(
        response=FakeResponse(status=200, body='{"name": "Widget"}')  # missing id
    )

    with pytest.raises(HttpkitValidationError):
        _ = await client.arequest(url="/products", response_model=Product)


async def test_response_model_with_non_json_body_raises_validation_error(
    make_async_client: MakeAsyncClient,
):
    """
    With a response_model, a non-JSON body raises a validation error.
    """
    client, _ = make_async_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError):
        _ = await client.arequest(url="/products", response_model=Product)


async def test_non_json_body_without_response_model_raises_validation_error(
    make_async_client: MakeAsyncClient,
):
    """
    Without a response_model, a non-JSON body cannot be decoded and raises a validation error.
    """
    client, _ = make_async_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError):
        _ = await client.arequest(url="/products")


async def test_validation_error_carries_context(make_async_client: MakeAsyncClient):
    """
    A validation error carries the request context (status code, method, url).
    """
    client, _ = make_async_client(response=FakeResponse(status=200, body="not json"))

    with pytest.raises(HttpkitValidationError) as err:
        _ = await client.arequest(url="/products", method=HTTPMethod.POST)

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
async def test_transport_errors_propagate_untouched(
    make_async_client: MakeAsyncClient, raised: HttpkitTransportError
):
    """
    Transport-layer errors bubble up unchanged, with retryability preserved.
    """
    client, _ = make_async_client(raises=raised)

    with pytest.raises(HttpkitTransportError) as err:
        _ = await client.arequest(url="/products")

    assert err.value is raised
    assert err.value.is_retryable() is raised.is_retryable()


# Response metadata


async def test_response_surfaces_status_code_and_headers(
    make_async_client: MakeAsyncClient,
):
    """
    The status code and headers from the raw response are surfaced on the Response.
    """
    client, _ = make_async_client(
        response=FakeResponse(status=200, body='{"a": 1}', headers={"X-Trace": "abc"})
    )

    response = await client.arequest(url="/products")

    assert response.status_code == 200
    assert response.headers == {"X-Trace": "abc"}
    assert response.payload == {"a": 1}
