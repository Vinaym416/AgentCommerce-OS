
"""
AGENTCOMMERCE OS
PHASE 12 — PAYMENT STATE MACHINE

Responsible only for deterministic server-side payment state.

IMPORTANT:
- AI agents never control payment state.
- Only verified payment events may change payment state.
- Webhook events may arrive out of order.
- Duplicate events must be safe.
- Payment state must never move backwards.
- Terminal states cannot be changed.
- This class does NOT access MongoDB.
- This class does NOT call Razorpay.

Flow:

Razorpay
    ↓
Verified Webhook
    ↓
PaymentService
    ↓
PaymentStateMachine
    ↓
PaymentRepository
"""


from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ============================================================
# PAYMENT STATES
# ============================================================


class PaymentState(str, Enum):

    CREATED = "CREATED"

    CHECKOUT_STARTED = "CHECKOUT_STARTED"

    AUTHORIZED = "AUTHORIZED"

    CAPTURED = "CAPTURED"

    ORDER_CONFIRMED = "ORDER_CONFIRMED"

    PAYMENT_FAILED = "PAYMENT_FAILED"

    PAYMENT_TIMEOUT = "PAYMENT_TIMEOUT"

    WEBHOOK_PENDING = "WEBHOOK_PENDING"

    VERIFICATION_FAILED = "VERIFICATION_FAILED"

    CANCELLED = "CANCELLED"


# ============================================================
# RESULT
# ============================================================


@dataclass
class StateTransitionResult:

    success: bool

    previous_state: str

    current_state: str

    changed: bool

    reason: str

    event: Optional[str]

    timestamp: str


# ============================================================
# SUCCESSFUL PAYMENT ORDER
# ============================================================

STATE_PRIORITY = {

    PaymentState.CREATED.value: 0,

    PaymentState.CHECKOUT_STARTED.value: 1,

    PaymentState.AUTHORIZED.value: 2,

    PaymentState.CAPTURED.value: 3,

    PaymentState.ORDER_CONFIRMED.value: 4,
}


# ============================================================
# TERMINAL STATES
# ============================================================

TERMINAL_STATES = {

    PaymentState.ORDER_CONFIRMED.value,

    PaymentState.PAYMENT_FAILED.value,

    PaymentState.PAYMENT_TIMEOUT.value,

    PaymentState.VERIFICATION_FAILED.value,

    PaymentState.CANCELLED.value,
}


# ============================================================
# PAYMENT STATE MACHINE
# ============================================================


class PaymentStateMachine:

    def __init__(
        self,
        initial_state: str = PaymentState.CREATED.value,
    ):

        valid_states = {
            state.value
            for state in PaymentState
        }

        if initial_state not in valid_states:

            raise ValueError(
                f"Invalid initial payment state: "
                f"{initial_state}"
            )

        self.state = initial_state

    # ========================================================
    # CURRENT STATE
    # ========================================================

    def get_state(self) -> str:

        return self.state

    # ========================================================
    # GENERIC TRANSITION
    # ========================================================

    def transition(
        self,
        new_state: str,
        *,
        event: Optional[str] = None,
        reason: str = "",
    ) -> StateTransitionResult:

        previous_state = self.state

        # ----------------------------------------------------
        # VALID STATE
        # ----------------------------------------------------

        valid_states = {
            state.value
            for state in PaymentState
        }

        if new_state not in valid_states:

            return self._result(
                success=False,
                previous_state=previous_state,
                current_state=self.state,
                changed=False,
                reason="invalid_payment_state",
                event=event,
            )

        # ----------------------------------------------------
        # SAME STATE
        # ----------------------------------------------------

        if new_state == previous_state:

            return self._result(
                success=True,
                previous_state=previous_state,
                current_state=self.state,
                changed=False,
                reason=(
                    reason
                    or "payment_state_already_current"
                ),
                event=event,
            )

        # ----------------------------------------------------
        # TERMINAL STATE
        # ----------------------------------------------------

        if previous_state in TERMINAL_STATES:

            return self._result(
                success=False,
                previous_state=previous_state,
                current_state=self.state,
                changed=False,
                reason="payment_state_is_terminal",
                event=event,
            )

        # ----------------------------------------------------
        # FAILURE / CANCELLATION
        # ----------------------------------------------------

        if new_state in {
            PaymentState.PAYMENT_FAILED.value,
            PaymentState.PAYMENT_TIMEOUT.value,
            PaymentState.VERIFICATION_FAILED.value,
            PaymentState.CANCELLED.value,
        }:

            self.state = new_state

            return self._result(
                success=True,
                previous_state=previous_state,
                current_state=self.state,
                changed=True,
                reason=(
                    reason
                    or "payment_failure_state_recorded"
                ),
                event=event,
            )

        # ----------------------------------------------------
        # SUCCESSFUL FLOW PRIORITY
        # ----------------------------------------------------

        previous_priority = STATE_PRIORITY.get(
            previous_state
        )

        new_priority = STATE_PRIORITY.get(
            new_state
        )

        if (
            previous_priority is None
            or new_priority is None
        ):

            return self._result(
                success=False,
                previous_state=previous_state,
                current_state=self.state,
                changed=False,
                reason="state_transition_priority_unknown",
                event=event,
            )

        # ----------------------------------------------------
        # OUT-OF-ORDER EVENT
        # ----------------------------------------------------

        if new_priority < previous_priority:

            return self._result(
                success=True,
                previous_state=previous_state,
                current_state=self.state,
                changed=False,
                reason="out_of_order_event_ignored",
                event=event,
            )

        # ----------------------------------------------------
        # VALID FORWARD TRANSITION
        # ----------------------------------------------------

        self.state = new_state

        return self._result(
            success=True,
            previous_state=previous_state,
            current_state=self.state,
            changed=True,
            reason=(
                reason
                or "payment_state_transitioned"
            ),
            event=event,
        )

    # ========================================================
    # RAZORPAY EVENT
    # ========================================================

    def process_event(
        self,
        event: str,
    ) -> StateTransitionResult:

        event_mapping = {

            "payment.authorized":
                PaymentState.AUTHORIZED.value,

            "payment.captured":
                PaymentState.CAPTURED.value,

            "payment.failed":
                PaymentState.PAYMENT_FAILED.value,

            "order.paid":
                PaymentState.ORDER_CONFIRMED.value,
        }

        # ----------------------------------------------------
        # UNKNOWN EVENT
        # ----------------------------------------------------

        if event not in event_mapping:

            return self._result(
                success=False,
                previous_state=self.state,
                current_state=self.state,
                changed=False,
                reason="unsupported_payment_event",
                event=event,
            )

        # ----------------------------------------------------
        # PROCESS EVENT
        # ----------------------------------------------------

        new_state = event_mapping[event]

        return self.transition(
            new_state,
            event=event,
            reason=(
                f"payment_state_updated_from_{event}"
            ),
        )

    # ========================================================
    # BACKWARD-COMPATIBILITY ALIAS
    # ========================================================

    def apply_event(
        self,
        event: str,
    ) -> StateTransitionResult:

        """
        Alias used by PaymentService.

        Keeps older code compatible while the canonical
        method remains process_event().
        """

        return self.process_event(event)

    # ========================================================
    # TERMINAL CHECK
    # ========================================================

    def is_terminal(self) -> bool:

        return self.state in TERMINAL_STATES

    # ========================================================
    # RESULT BUILDER
    # ========================================================

    def _result(
        self,
        *,
        success: bool,
        previous_state: str,
        current_state: str,
        changed: bool,
        reason: str,
        event: Optional[str],
    ) -> StateTransitionResult:

        return StateTransitionResult(

            success=success,

            previous_state=previous_state,

            current_state=current_state,

            changed=changed,

            reason=reason,

            event=event,

            timestamp=datetime.now(
                timezone.utc
            ).isoformat(),
        )


# ============================================================
# CLI TESTS
# ============================================================


def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS — PAYMENT STATE MACHINE")
    print("=" * 80)

    # ========================================================
    # TEST 1
    # NORMAL PAYMENT FLOW
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 1 — NORMAL PAYMENT FLOW")
    print("-" * 80)

    machine = PaymentStateMachine()

    events = [
        "payment.authorized",
        "payment.captured",
        "order.paid",
    ]

    for event in events:

        result = machine.process_event(event)

        print(result)

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 2
    # PAYMENT FAILURE
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 2 — PAYMENT FAILURE")
    print("-" * 80)

    machine = PaymentStateMachine()

    result = machine.process_event(
        "payment.failed"
    )

    print(result)

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 3
    # OUT-OF-ORDER
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 3 — OUT-OF-ORDER EVENTS")
    print("-" * 80)

    machine = PaymentStateMachine()

    result = machine.process_event(
        "payment.captured"
    )

    print(
        "Captured:",
        result,
    )

    result = machine.process_event(
        "payment.authorized"
    )

    print(
        "Late authorized:",
        result,
    )

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 4
    # DUPLICATE
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 4 — DUPLICATE EVENT")
    print("-" * 80)

    machine = PaymentStateMachine()

    result = machine.process_event(
        "payment.captured"
    )

    print(
        "First captured:",
        result,
    )

    result = machine.process_event(
        "payment.captured"
    )

    print(
        "Second captured:",
        result,
    )

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 5
    # BACKWARD TRANSITION
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 5 — BACKWARD TRANSITION")
    print("-" * 80)

    machine = PaymentStateMachine(
        initial_state=PaymentState.CAPTURED.value
    )

    result = machine.transition(
        PaymentState.AUTHORIZED.value
    )

    print(result)

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 6
    # FAILED → CAPTURED
    # ========================================================

    print("\n")
    print("-" * 80)
    print(
        "TEST 6 — FAILED PAYMENT CANNOT BECOME CAPTURED"
    )
    print("-" * 80)

    machine = PaymentStateMachine()

    result = machine.process_event(
        "payment.failed"
    )

    print(
        "Payment failed:",
        result,
    )

    result = machine.process_event(
        "payment.captured"
    )

    print(
        "Late captured:",
        result,
    )

    print(
        "\nFinal state:",
        machine.get_state(),
    )

    # ========================================================
    # TEST 7
    # UNSUPPORTED EVENT
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 7 — UNSUPPORTED EVENT")
    print("-" * 80)

    machine = PaymentStateMachine()

    result = machine.process_event(
        "payment.refunded"
    )

    print(result)

    print(
        "\nFinal state:",
        machine.get_state(),
    )


if __name__ == "__main__":

    main()

