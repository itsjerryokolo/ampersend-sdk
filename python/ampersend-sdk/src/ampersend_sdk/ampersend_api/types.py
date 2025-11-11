from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
)


class PaymentEventType(str, Enum):
    """Payment event types."""

    SENDING = "sending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class ApiClientOptions(BaseModel):
    """Configuration options for the API client."""

    base_url: str
    session_key_private_key: Optional[str] = None
    timeout: int = 30000


class AuthenticationState(BaseModel):
    """Current authentication state."""

    token: Optional[str] = None
    agent_address: Optional[str] = None
    expires_at: Optional[datetime] = None


class PaymentEvent(BaseModel):
    """Payment lifecycle event."""

    event_type: PaymentEventType = Field(serialization_alias="type")
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class ApiRequestAgentPaymentAuthorization(BaseModel):
    """Agent payment authorization request."""

    requirements: List[PaymentRequirements]
    context: Dict[str, Any] | None  # TODO: missing alias generation


class ApiResponseAgentPaymentAuthorization(BaseModel):
    """Agent payment authorization response."""

    authorized: bool
    reason: Optional[str] = Field(
        default=None, description="Reason for denial if not authorized"
    )
    limits: Optional[Dict[str, str]] = Field(
        default=None,
        description="Remaining spend limits with daily_remaining and monthly_remaining",
    )


class ApiRequestAgentPaymentEvent(BaseModel):
    """Agent payment event report."""

    id_: str = Field(serialization_alias="id")
    payment: PaymentPayload
    event: PaymentEvent


class ApiResponseAgentPaymentEvent(BaseModel):
    """Agent payment event response."""

    received: bool
    payment_id: Optional[str] = Field(
        default=None,
        description="Internal payment record ID if created",
        validation_alias="paymentId",
    )

    model_config = ConfigDict(
        validate_by_name=True,
    )


class ApiResponseNonce(BaseModel):
    """Nonce response."""

    nonce: str
    session_id: str = Field(validation_alias="sessionId")

    model_config = ConfigDict(
        validate_by_name=True,
    )


class ApiRequestLogin(BaseModel):
    """SIWE login request."""

    message: str
    signature: str
    session_id: str = Field(serialization_alias="sessionId")


class ApiResponseLogin(BaseModel):
    """SIWE login response."""

    token: str
    agent_address: str = Field(validation_alias="agentAddress")
    expires_at: str = Field(validation_alias="expiresAt")

    model_config = ConfigDict(
        validate_by_name=True,
    )


class ApiError(Exception):
    """Custom API error with optional status code and response."""

    def __init__(
        self, message: str, status: Optional[int] = None, response: Optional[Any] = None
    ):
        self.status = status
        self.response = response
        super().__init__(message)
