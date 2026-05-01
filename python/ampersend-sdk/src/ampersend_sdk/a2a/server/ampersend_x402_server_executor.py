"""x402 server executor that gates payments through the Ampersend
compliance API before delegating to the facilitator.

The executor wraps `FacilitatorX402ServerExecutor`. On `verify_payment`
it first calls Ampersend's `POST /v1/agents/:address/payment/authorize-
receipt` over a SIWE-authenticated bearer token; if compliance denies,
it returns a `VerifyResponse` with `is_valid=False` and the
human-readable reason carried through. If compliance allows, it
delegates to the facilitator's verify path so on-chain settlement
still happens via the configured facilitator.

Settlement is unchanged — it still goes straight to the facilitator
because by the time we settle, the gate has already approved.
"""

from typing import Any

from x402_a2a import (
    FacilitatorConfig,
    x402ExtensionConfig,
)
from x402_a2a.types import (
    AgentExecutor,
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
)

from ...ampersend.client import ApiClient
from .facilitator_x402_server_executor import FacilitatorX402ServerExecutor
from .x402_server_executor import X402ServerExecutorFactory


class AmpersendX402ServerExecutor(FacilitatorX402ServerExecutor):
    """Compliance-gated x402 server executor.

    Args:
        delegate: The wrapped agent executor (handles the underlying
            request once payment is verified).
        config: x402 extension config (passed through to the base
            executor).
        api_client: An Ampersend `ApiClient` configured with the
            seller agent's address and session-key private key. The
            client's SIWE flow runs lazily on first `authorize_receipt`
            call. Re-uses the client used by the buyer side for
            agents that both buy and sell.
        facilitator_config: Optional facilitator config for the
            verify/settle delegation.
    """

    def __init__(
        self,
        *,
        delegate: AgentExecutor,
        config: x402ExtensionConfig,
        api_client: ApiClient,
        facilitator_config: FacilitatorConfig | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            delegate=delegate,
            config=config,
            facilitator_config=facilitator_config,
            **kwargs,
        )
        self._api_client = api_client

    async def verify_payment(
        self, payload: PaymentPayload, requirements: PaymentRequirements
    ) -> VerifyResponse:
        """Compliance-gate the payment, then delegate to the facilitator.

        On compliance deny, returns `VerifyResponse(is_valid=False,
        invalid_reason=<reason>)` so the upstream task layer surfaces
        a 402 with the structured reason. On allow, the call falls
        through to the facilitator's normal verify (signature, amount,
        nonce reuse, etc.).
        """
        # PaymentPayload.payload is the typed ExactPaymentPayload —
        # not a dict. EIP3009Authorization.from_ uses an underscore
        # because `from` is a Python keyword; the field's wire alias
        # is "from".
        authorization = payload.payload.authorization
        compliance_result = await self._api_client.authorize_receipt(
            payer_address=authorization.from_,
            payment_requirements=requirements,
            nonce=authorization.nonce,
            payment_signature=payload.payload.signature,
        )

        if not compliance_result.authorized:
            return VerifyResponse(
                isValid=False,
                invalidReason=compliance_result.reason
                or "Payment denied by compliance",
                payer=authorization.from_,
            )

        # Compliance allowed — delegate to the facilitator for the
        # standard x402 signature/amount/nonce checks.
        return await super().verify_payment(payload, requirements)


def create_ampersend_executor_factory(
    api_client: ApiClient,
    facilitator_config: FacilitatorConfig | None = None,
    **kwargs: Any,
) -> X402ServerExecutorFactory:
    """Create a factory for `AmpersendX402ServerExecutor` instances.

    Args:
        api_client: The Ampersend API client (configured with the
            seller agent's address + session-key private key).
        facilitator_config: Optional facilitator configuration.
        **kwargs: Additional kwargs forwarded to the executor
            constructor.

    Returns:
        Factory function suitable for `X402A2aAgentExecutor.x402_executor_factory`.

    Example:
        >>> from ampersend_sdk.ampersend import ApiClient, ApiClientOptions
        >>> client = ApiClient(ApiClientOptions(
        ...     base_url="https://api.staging.ampersend.ai",
        ...     agent_address="0x...",
        ...     session_key_private_key="0x...",
        ... ))
        >>> factory = create_ampersend_executor_factory(
        ...     api_client=client,
        ...     facilitator_config=FacilitatorConfig(
        ...         url="https://facilitator.example.com"
        ...     ),
        ... )
    """

    def factory(
        *,
        delegate: AgentExecutor,
        config: x402ExtensionConfig,
    ) -> AmpersendX402ServerExecutor:
        return AmpersendX402ServerExecutor(
            delegate=delegate,
            config=config,
            api_client=api_client,
            facilitator_config=facilitator_config,
            **kwargs,
        )

    return factory
