"""
AGENTCOMMERCE OS — REAL RAZORPAY INTEGRATION TEST

Tests REAL Razorpay API integration with 3 core test cases:
1. Razorpay client credentials validation
2. HMAC signature verification
3. Full real payment flow (order creation → payment verification)

Run to verify real Razorpay integration:

    cd Backend
    .\.venv\Scripts\activate
    python script/tests/test_real_razorpay_integration.py

Requirements:
- .env file with RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
- MongoDB Atlas connection working
- Python 3.11+ with venv activated
- Internet connection (real Razorpay API calls in test mode)
"""

import sys
import os
import json
import hmac
import hashlib
from uuid import uuid4

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from script.agents.commerce_execution_agent import CommerceExecutionAgent
from script.payment.razorpay_client import RazorpayClient
from script.payment.payment_verifier import PaymentVerifier
from script.database.repositories.transaction_repository import TransactionRepository
from script.database.repositories.order_repository import OrderRepository


def test_razorpay_client_credentials():
    """
    Test 1: Verify RazorpayClient has valid credentials from .env
    """
    
    print("\n" + "="*70)
    print("TEST 1: RAZORPAY CLIENT CREDENTIALS")
    print("="*70)
    
    client = RazorpayClient()
    
    assert client.key_id is not None, "RAZORPAY_KEY_ID not set in .env"
    assert client.key_secret is not None, "RAZORPAY_KEY_SECRET not set in .env"
    
    print(f"✅ Key ID: {client.key_id}")
    print(f"✅ Key Secret: {'*' * len(client.key_secret)}")
    print(f"✅ Base URL: {client.BASE_URL}")
    
    print("\n" + "="*70)
    print("✅ TEST 1 PASSED: CREDENTIALS CONFIGURED!")
    print("="*70)


def test_payment_verifier_signature():
    """
    Test 2: Verify PaymentVerifier can validate HMAC signatures
    """
    
    print("\n" + "="*70)
    print("TEST 2: PAYMENT VERIFIER SIGNATURE VALIDATION")
    print("="*70)
    
    verifier = PaymentVerifier()
    
    # Create test data
    order_id = "order_test_12345"
    payment_id = "pay_test_67890"
    # PaymentVerifier uses RAZORPAY_KEY_SECRET for HMAC (not WEBHOOK_SECRET)
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    
    # Generate valid signature
    message = f"{order_id}|{payment_id}"
    valid_signature = hmac.new(
        key_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Order ID: {order_id}")
    print(f"Payment ID: {payment_id}")
    print(f"Valid Signature: {valid_signature[:20]}...")
    
    # Test 1: Valid signature should verify
    print("\n[1/2] Testing valid signature...")
    result = verifier.verify_payment_signature(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=valid_signature
    )
    
    assert result.valid, f"Valid signature rejected: {result.reason}"
    print(f"✅ Valid signature accepted: {result.status}")
    
    # Test 2: Invalid signature should reject
    print("\n[2/2] Testing invalid signature...")
    invalid_signature = "invalid_signature_12345"
    result = verifier.verify_payment_signature(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=invalid_signature
    )
    
    assert not result.valid, "Invalid signature was accepted (should be rejected)"
    print(f"✅ Invalid signature rejected: {result.reason}")
    
    print("\n" + "="*70)
    print("✅ TEST 2 PASSED: SIGNATURE VERIFICATION WORKS!")
    print("="*70)


def test_real_razorpay_payment_flow():
    """
    Test 3: Full real Razorpay payment flow
    
    This tests:
    1. RazorpayClient.create_order() with REAL Razorpay API
    2. CommerceExecutionAgent.execute() returns RAZORPAY_ORDER_CREATED
    3. CommerceExecutionAgent.verify_payment() creates order
    4. MongoDB stores transaction + order
    """
    
    print("\n" + "="*70)
    print("TEST 3: REAL RAZORPAY PAYMENT FLOW")
    print("="*70)
    
    # Step 1: Create payment order with REAL Razorpay
    print("\n[1/5] Creating payment order with REAL Razorpay API...")
    
    agent = CommerceExecutionAgent()
    
    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="CARD",
        execute_payment=True
    )
    
    # The backend accepts payment instrument names like CARD/UPI, not the gateway label RAZORPAY.
    # With execute_payment=True, it creates the Razorpay order and stores the transaction.
    razorpay_order = result.get('razorpay_order')
    
    if razorpay_order is None or razorpay_order.get('status') != 'RAZORPAY_ORDER_CREATED':
        print(f"❌ Razorpay order creation failed!")
        print(f"Full result: {json.dumps(result, indent=2, default=str)}")
        raise AssertionError(f"Razorpay order not created. Status: {None if razorpay_order is None else razorpay_order.get('status')}")
    
    assert razorpay_order.get('success') == True, f"Razorpay order failed: {razorpay_order}"
    
    print(f"✅ Razorpay Order Created!")
    print(f"   Order ID: {razorpay_order['razorpay_order_id']}")
    print(f"   Amount: ₹{razorpay_order['amount_in_paise'] / 100}")
    print(f"   Status: {razorpay_order['razorpay_status']}")
    
    order_id = razorpay_order['razorpay_order_id']
    transaction_id = razorpay_order['transaction_id']
    final_price = razorpay_order['amount_in_paise'] / 100
    
    # Step 2: Check transaction stored in MongoDB
    print("\n[2/5] Checking transaction in MongoDB...")
    
    tx_repo = TransactionRepository()
    transaction = tx_repo.get_by_transaction_id(transaction_id)
    
    assert transaction is not None, f"Transaction {transaction_id} not found in MongoDB"
    print(f"✅ Transaction found in MongoDB!")
    print(f"   Status: {transaction.get('status')}")
    print(f"   Payment Status: {transaction.get('payment_status')}")
    print(f"   Amount: ₹{transaction.get('final_price')}")
    
    # Step 3: Simulate Razorpay completing payment
    print("\n[3/5] Simulating Razorpay payment completion...")
    print("   (In real scenario, user completes payment in Razorpay Checkout)")
    
    # Use a fresh payment ID per run to match real Razorpay behavior.
    # Reusing a payment_id would violate the MongoDB uniqueness constraint.
    payment_id = f"pay_{uuid4().hex[:16]}"
    
    # Create valid signature for this payment
    # PaymentVerifier uses RAZORPAY_KEY_SECRET, not WEBHOOK_SECRET
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    message = f"{order_id}|{payment_id}"
    razorpay_signature = hmac.new(
        key_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"   Order ID: {order_id}")
    print(f"   Payment ID: {payment_id}")
    print(f"   Signature: {razorpay_signature[:20]}...")
    
    # Step 4: Verify payment
    print("\n[4/5] Verifying payment with PaymentVerifier...")
    
    verify_result = agent.verify_payment(
        customer_id=None,  # Will load from transaction
        transaction_id=transaction_id,
        product_id=None,
        product_price=None,
        discount_percent=None,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=razorpay_signature
    )
    
    print(f"Status: {verify_result['final_action']}")
    assert verify_result['final_action'] == 'ORDER_CREATED', f"Expected ORDER_CREATED, got {verify_result['final_action']}"
    
    order = verify_result['order']
    order_internal_id = order['order_id']
    
    print(f"✅ Payment Verified!")
    print(f"   Internal Order ID: {order_internal_id}")
    print(f"   Status: {order['status']}")
    
    # Step 5: Check order stored in MongoDB
    print("\n[5/5] Checking order in MongoDB...")
    
    order_repo = OrderRepository()
    stored_order = order_repo.find_by_order_id(order_internal_id)
    
    assert stored_order is not None, f"Order {order_internal_id} not found in MongoDB"
    print(f"✅ Order found in MongoDB!")
    print(f"   Order ID: {stored_order.get('order_id')}")
    print(f"   Status: {stored_order.get('status')}")
    print(f"   Payment Transaction: {stored_order.get('payment_transaction_id')}")
    
    # Verify amounts match
    assert stored_order.get('amount') == final_price, "Order amount mismatch"
    
    print("\n" + "="*70)
    print("✅ TEST 3 PASSED: REAL RAZORPAY FLOW WORKS!")
    print("="*70)
    
    return {
        'transaction_id': transaction_id,
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': razorpay_signature,
        'internal_order_id': order_internal_id,
        'amount': final_price
    }


def main():
    """Run all real Razorpay integration tests"""
    
    print("\n" + "="*70)
    print("AGENTCOMMERCE OS — REAL RAZORPAY INTEGRATION TESTS")
    print("="*70)
    print("Testing REAL Razorpay API integration (not fake clients)")
    print("Razorpay Test Mode Credentials:")
    print(f"  - KEY_ID: {os.getenv('RAZORPAY_KEY_ID', 'NOT SET')}")
    print(f"  - KEY_SECRET: {'SET' if os.getenv('RAZORPAY_KEY_SECRET') else 'NOT SET'}")
    
    try:
        # Test 1: Razorpay client credentials
        test_razorpay_client_credentials()
        
        # Test 2: Signature verification
        test_payment_verifier_signature()
        
        # Test 3: Full payment flow
        test_result = test_real_razorpay_payment_flow()
        
        # Summary
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        print("\nYour real Razorpay integration is working correctly!")
        print("\nNext steps:")
        print("1. Start FastAPI backend: uvicorn api.main:app --reload")
        print("2. Start Frontend: npm run dev")
        print("3. Open http://localhost:5173")
        print("4. Use PaymentFlow component to test end-to-end")
        print("5. Use test card: 4111 1111 1111 1111")
        print("\nFlow summary:")
        print(f"  Transaction ID: {test_result['transaction_id']}")
        print(f"  Razorpay Order: {test_result['razorpay_order_id']}")
        print(f"  Amount: ₹{test_result['amount']}")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
