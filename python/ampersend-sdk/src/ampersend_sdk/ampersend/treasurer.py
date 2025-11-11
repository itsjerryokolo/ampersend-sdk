import datetime
import uuid
from typing import Any, Dict

from x402_a2a.types import (
    PaymentStatus,
    x402PaymentRequiredResponse,
)

from ampersend_sdk.x402 import X402Authorization, X402Treasurer, X402Wallet

from .client import ApiClient
from .types import PaymentEvent, PaymentEventType


class AmpersendTreasurer(X402Treasurer):
    """
    Ampersend API treasurer with authorization checks and event reporting.

    Works with both EOA and smart account payment methods via the
    X402Wallet protocol.
    """

    def __init__(self, api_client: ApiClient, wallet: X402Wallet):
        """
        Initialize Ampersend treasurer.

        Args:
            api_client: ApiClient instance for authorization checks
            wallet: X402Wallet for creating payment payloads
        """
        self._api_client = api_client
        self._wallet = wallet

    async def onPaymentRequired(
        self,
        payment_required: x402PaymentRequiredResponse,
        context: Dict[str, Any] | None = None,
    ) -> X402Authorization | None:
        result = await self._api_client.authorize_payment(
            payment_required.accepts, context
        )

        if not result.authorized:
            return None

        # TODO: actually pick based on result.selectedRequirement
        payment = self._wallet.create_payment(
            requirements=payment_required.accepts[0],
        )
        authorization_id = uuid.uuid4().hex

        await self._api_client.report_payment_event(
            event_id=authorization_id,
            payment=payment,
            event=PaymentEvent(
                event_type=PaymentEventType.SENDING,
                timestamp=datetime.datetime.now(datetime.UTC),
                details=context,
            ),
        )

        return X402Authorization(authorization_id=authorization_id, payment=payment)

    async def onStatus(
        self,
        status: PaymentStatus,
        authorization: X402Authorization,
        context: Dict[str, Any] | None = None,
    ) -> None:
        statusToEventType = {
            PaymentStatus.PAYMENT_SUBMITTED: PaymentEventType.SENDING,
            PaymentStatus.PAYMENT_FAILED: PaymentEventType.ERROR,
            PaymentStatus.PAYMENT_REJECTED: PaymentEventType.REJECTED,
            PaymentStatus.PAYMENT_VERIFIED: PaymentEventType.ACCEPTED,
            PaymentStatus.PAYMENT_COMPLETED: PaymentEventType.ACCEPTED,
        }
        # sending, accepted, rejected or error
        if status not in statusToEventType:
            return

        await self._api_client.report_payment_event(
            event_id=authorization.authorization_id,
            payment=authorization.payment,
            event=PaymentEvent(
                event_type=statusToEventType[status],
                timestamp=datetime.datetime.now(datetime.UTC),
                details=context,
            ),
        )
