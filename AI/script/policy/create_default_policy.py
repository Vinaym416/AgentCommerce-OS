import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_PATH = BASE_DIR / "data" / "policies" / "merchant_policy.json"


DEFAULT_POLICY = {
    "merchant_id": "demo_merchant_001",
    "merchant_name": "Demo Merchant",

    "currency": "INR",

    "discount_policy": {
        "enabled": True,

        "max_discount_percent": 15,

        "minimum_margin_percent": 10,

        "allow_dynamic_discount": True,

        "discount_requires_high_intent": True
    },

    "negotiation_policy": {
        "enabled": True,

        "max_rounds": 3,

        "minimum_order_value": 500,

        "maximum_discount_requests": 2
    },

    "approval_policy": {
        "auto_approve_below": 2000,

        "require_approval_above": 10000
    },

    "payment_policy": {
        "allowed_methods": [
            "upi",
            "card",
            "netbanking"
        ]
    },

    "agent_permissions": {
        "can_recommend_products": True,

        "can_negotiate_price": True,

        "can_apply_discount": True,

        "can_create_payment_order": True,

        "can_execute_payment": False
    }
}


def main():

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            DEFAULT_POLICY,
            f,
            indent=4
        )

    print("=" * 80)
    print("AGENTCOMMERCE OS - DEFAULT MERCHANT POLICY")
    print("=" * 80)

    print()
    print(f"Created: {OUTPUT_PATH}")
    print()

    print("Merchant:")
    print(f"  ID       : {DEFAULT_POLICY['merchant_id']}")
    print(f"  Name     : {DEFAULT_POLICY['merchant_name']}")
    print(f"  Currency : {DEFAULT_POLICY['currency']}")

    print()
    print("Discount Policy:")
    print(
        f"  Enabled              : "
        f"{DEFAULT_POLICY['discount_policy']['enabled']}"
    )
    print(
        f"  Maximum discount     : "
        f"{DEFAULT_POLICY['discount_policy']['max_discount_percent']}%"
    )
    print(
        f"  Minimum margin       : "
        f"{DEFAULT_POLICY['discount_policy']['minimum_margin_percent']}%"
    )

    print()
    print("Negotiation Policy:")
    print(
        f"  Enabled              : "
        f"{DEFAULT_POLICY['negotiation_policy']['enabled']}"
    )
    print(
        f"  Maximum rounds       : "
        f"{DEFAULT_POLICY['negotiation_policy']['max_rounds']}"
    )

    print()
    print("Approval Policy:")
    print(
        f"  Auto approve below   : "
        f"₹{DEFAULT_POLICY['approval_policy']['auto_approve_below']}"
    )
    print(
        f"  Approval above       : "
        f"₹{DEFAULT_POLICY['approval_policy']['require_approval_above']}"
    )

    print()
    print("Agent Permissions:")

    for key, value in DEFAULT_POLICY["agent_permissions"].items():
        print(f"  {key:<25}: {value}")

    print()
    print("POLICY CREATED")
    print("=" * 80)


if __name__ == "__main__":
    main()