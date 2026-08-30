import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

POLICY_PATH = (
    BASE_DIR
    / "data"
    / "policies"
    / "merchant_policy.json"
)


REQUIRED_FIELDS = [
    "merchant_id",
    "merchant_name",
    "currency",
    "discount_policy",
    "negotiation_policy",
    "approval_policy",
    "payment_policy",
    "agent_permissions"
]


def load_policy():

    with open(
        POLICY_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def validate_policy(policy):

    errors = []

    # --------------------------------------------------
    # Top-level fields
    # --------------------------------------------------

    for field in REQUIRED_FIELDS:

        if field not in policy:
            errors.append(
                f"Missing required field: {field}"
            )

    if errors:
        return errors

    # --------------------------------------------------
    # Discount validation
    # --------------------------------------------------

    discount = policy["discount_policy"]

    max_discount = discount.get(
        "max_discount_percent"
    )

    minimum_margin = discount.get(
        "minimum_margin_percent"
    )

    if not 0 <= max_discount <= 100:

        errors.append(
            "max_discount_percent must be between 0 and 100"
        )

    if not 0 <= minimum_margin <= 100:

        errors.append(
            "minimum_margin_percent must be between 0 and 100"
        )

    # --------------------------------------------------
    # Negotiation validation
    # --------------------------------------------------

    negotiation = policy["negotiation_policy"]

    max_rounds = negotiation.get("max_rounds")

    minimum_order_value = negotiation.get(
        "minimum_order_value"
    )

    if max_rounds < 1:

        errors.append(
            "max_rounds must be at least 1"
        )

    if minimum_order_value < 0:

        errors.append(
            "minimum_order_value cannot be negative"
        )

    # --------------------------------------------------
    # Approval validation
    # --------------------------------------------------

    approval = policy["approval_policy"]

    auto_approve = approval.get(
        "auto_approve_below"
    )

    require_approval = approval.get(
        "require_approval_above"
    )

    if auto_approve < 0:

        errors.append(
            "auto_approve_below cannot be negative"
        )

    if require_approval < auto_approve:

        errors.append(
            "require_approval_above must be "
            "greater than or equal to auto_approve_below"
        )

    # --------------------------------------------------
    # Payment validation
    # --------------------------------------------------

    allowed_methods = policy[
        "payment_policy"
    ].get("allowed_methods", [])

    if not allowed_methods:

        errors.append(
            "At least one payment method must be allowed"
        )

    # --------------------------------------------------
    # Agent permission validation
    # --------------------------------------------------

    permissions = policy[
        "agent_permissions"
    ]

    for key, value in permissions.items():

        if not isinstance(value, bool):

            errors.append(
                f"Agent permission '{key}' must be boolean"
            )

    return errors


def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS - POLICY VALIDATION")
    print("=" * 80)

    print()
    print(f"Policy: {POLICY_PATH}")
    print()

    policy = load_policy()

    errors = validate_policy(policy)

    if errors:

        print("POLICY INVALID")
        print()

        for error in errors:
            print(f"[ERROR] {error}")

        raise SystemExit(1)

    print("POLICY VALID")
    print()

    print("Merchant:")
    print(f"  {policy['merchant_name']}")

    print()
    print("Safety constraints:")
    print(
        f"  Maximum discount : "
        f"{policy['discount_policy']['max_discount_percent']}%"
    )
    print(
        f"  Minimum margin   : "
        f"{policy['discount_policy']['minimum_margin_percent']}%"
    )
    print(
        f"  Max negotiations : "
        f"{policy['negotiation_policy']['max_rounds']}"
    )

    print()
    print("All policy checks passed.")
    print("=" * 80)


if __name__ == "__main__":
    main()