"""Unit tests for API response models."""

from ampersend_sdk.ampersend.types import (
    ApiResponseAgentPaymentAuthorization,
    ApiResponseAgentPaymentEvent,
)


class TestApiResponseAgentPaymentAuth:
    """Test ApiResponseAgentPaymentAuthorization model."""

    def test_successful_authorization_with_limits(self) -> None:
        """Test successful authorization response with limits."""

        response = ApiResponseAgentPaymentAuthorization(
            authorized=True,
            limits={
                "dailyRemaining": "1000000000000000000",
                "monthlyRemaining": "30000000000000000000",
            },
        )

        assert response.authorized is True
        assert response.reason is None
        assert response.limits is not None
        assert response.limits["dailyRemaining"] == "1000000000000000000"
        assert response.limits["monthlyRemaining"] == "30000000000000000000"

    def test_denied_authorization_with_reason(self) -> None:
        """Test denied authorization response with reason."""
        response = ApiResponseAgentPaymentAuthorization(
            authorized=False, reason="Daily spend limit exceeded"
        )

        assert response.authorized is False
        assert response.reason == "Daily spend limit exceeded"
        assert response.limits is None

    def test_successful_authorization_no_limits(self) -> None:
        """Test successful authorization without limits."""

        response = ApiResponseAgentPaymentAuthorization(authorized=True)

        assert response.authorized is True
        assert response.reason is None
        assert response.limits is None

    def test_camel_case_parsing(self) -> None:
        """Test parsing with camelCase field names."""
        data = {
            "authorized": True,
            "limits": {
                "dailyRemaining": "500000000000000000",
                "monthlyRemaining": "15000000000000000000",
            },
        }

        response = ApiResponseAgentPaymentAuthorization.model_validate(data)

        assert response.authorized is True
        assert response.limits is not None
        assert response.limits["dailyRemaining"] == "500000000000000000"


class TestApiResponseAgentPaymentEvent:
    """Test ApiResponseAgentPaymentEvent model."""

    def test_event_received_with_payment_id(self) -> None:
        """Test event response with payment ID."""
        data = {"received": True, "paymentId": "payment_12345"}

        response = ApiResponseAgentPaymentEvent.model_validate(data)

        assert response.received is True
        assert response.payment_id == "payment_12345"

    def test_event_received_without_payment_id(self) -> None:
        """Test event response without payment ID."""

        response = ApiResponseAgentPaymentEvent(received=True)

        assert response.received is True
        assert response.payment_id is None

    def test_event_not_received(self) -> None:
        """Test event not received response."""
        response = ApiResponseAgentPaymentEvent(received=False)

        assert response.received is False
        assert response.payment_id is None

    def test_snake_case_parsing(self) -> None:
        """Test parsing with snake_case field names."""
        data = {"received": True, "payment_id": "payment_67890"}

        response = ApiResponseAgentPaymentEvent.model_validate(data)

        assert response.received is True
        assert response.payment_id == "payment_67890"

    def test_camel_case_parsing(self) -> None:
        """Test parsing with camelCase field names."""
        data = {"received": True, "paymentId": "payment_camel_case"}

        response = ApiResponseAgentPaymentEvent.model_validate(data)

        assert response.received is True
        assert response.payment_id == "payment_camel_case"
