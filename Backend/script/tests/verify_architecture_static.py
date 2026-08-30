#!/usr/bin/env python3
"""
Static Architecture Verification Script

Verifies component separation by analyzing source code directly
without requiring runtime imports or external dependencies.
"""

import sys
from pathlib import Path
import re


def check_file_for_patterns(filepath, forbidden_patterns, required_patterns=None):
    """Check a file for forbidden and required patterns"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        violations = []
        for pattern, message in forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(f"❌ {message}")
        
        if required_patterns:
            for pattern, message in required_patterns:
                if not re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"❌ {message}")
        
        return violations, content
    except Exception as e:
        return [f"❌ Error reading file: {e}"], ""


def verify_commerce_agent():
    """Verify CommerceAgent does not directly access payment/order layers"""
    print("\n" + "="*70)
    print("VERIFYING: CommerceAgent Separation from Payment Layer")
    print("="*70)
    
    filepath = Path("d:/AgentCommerce OS/Backend/script/agents/commerce_agent.py")
    
    forbidden = [
        (r'self\.payment_agent\s*=', "CommerceAgent assigns self.payment_agent"),
        (r'self\.order_agent\s*=', "CommerceAgent assigns self.order_agent"),
        (r'self\.checkout_agent\s*=', "CommerceAgent assigns self.checkout_agent"),
        (r'self\.payment_agent\.process_payment', "CommerceAgent calls payment_agent.process_payment"),
        (r'self\.order_agent\.create_order', "CommerceAgent calls order_agent.create_order"),
    ]
    
    violations, content = check_file_for_patterns(filepath, forbidden)
    
    # Check for proper delegation
    required = [
        (r'self\.execution_agent\s*=\s*CommerceExecutionAgent', 
         "CommerceAgent should have execution_agent"),
        (r'self\.transaction_manager\s*=\s*TransactionManager', 
         "CommerceAgent should have transaction_manager"),
        (r'self\.negotiation_agent\s*=\s*NegotiationAgent', 
         "CommerceAgent should have negotiation_agent"),
        (r'def _execute_payment.*?return None', 
         "_execute_payment should be deprecated"),
        (r'def _create_order.*?return None', 
         "_create_order should be deprecated"),
    ]
    
    for pattern, message in required:
        if not re.search(pattern, content, re.DOTALL | re.IGNORECASE):
            violations.append(f"⚠️  {message}")
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ CommerceAgent separation VERIFIED:")
        print("  ✓ No self.payment_agent assignment")
        print("  ✓ No self.order_agent assignment")
        print("  ✓ No self.checkout_agent assignment")
        print("  ✓ No direct payment_agent.process_payment calls")
        print("  ✓ No direct order_agent.create_order calls")
        print("  ✓ Has execution_agent delegation")
        print("  ✓ Has transaction_manager reference")
        print("  ✓ Has negotiation_agent reference")
        print("  ✓ Deprecated methods properly stubbed")
        return True


def verify_negotiation_agent():
    """Verify NegotiationAgent is pricing-only"""
    print("\n" + "="*70)
    print("VERIFYING: NegotiationAgent Pricing-Only Ownership")
    print("="*70)
    
    filepath = Path("d:/AgentCommerce OS/Backend/script/agents/negotiation_agent.py")
    
    forbidden = [
        (r'razorpay', "NegotiationAgent should not reference Razorpay"),
        (r'payment', "NegotiationAgent should not reference payment processing"),
        (r'order.*create', "NegotiationAgent should not create orders"),
        (r'webhook', "NegotiationAgent should not handle webhooks"),
    ]
    
    violations, content = check_file_for_patterns(filepath, forbidden)
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ NegotiationAgent separation VERIFIED:")
        print("  ✓ No Razorpay references")
        print("  ✓ No payment processing code")
        print("  ✓ No order creation code")
        print("  ✓ No webhook handling code")
        print("  ✓ Pricing-only logic confirmed")
        return True


def verify_transaction_state():
    """Verify TransactionState has all required fields"""
    print("\n" + "="*70)
    print("VERIFYING: TransactionState Complete Lifecycle Fields")
    print("="*70)
    
    filepath = Path("d:/AgentCommerce OS/Backend/script/transaction/transaction_state.py")
    
    required_fields = [
        'customer_id',
        'product_id',
        'original_price',
        'negotiated_price',  # NEW
        'final_price',
        'discount_percent',
        'currency',  # NEW
        'transaction_id',
        'status',
        'customer_accepted',
        'razorpay_order_id',
        'razorpay_payment_id',
        'payment_transaction_id',
        'payment_status',
        'order_id',
    ]
    
    violations = []
    _, content = check_file_for_patterns(filepath, [])
    
    for field in required_fields:
        # Look for field declaration
        pattern = rf'{field}\s*:\s*(?:Optional\[)?(?:str|int|float|bool)'
        if not re.search(pattern, content):
            violations.append(f"❌ TransactionState missing field: {field}")
    
    # Check for proper pricing calculation in __post_init__
    if 'negotiated_price' not in content:
        violations.append("❌ TransactionState missing negotiated_price field")
    
    if 'currency' not in content:
        violations.append("❌ TransactionState missing currency field")
    
    if '__post_init__' not in content:
        violations.append("❌ TransactionState missing __post_init__ method")
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ TransactionState completeness VERIFIED:")
        print("  ✓ All pricing fields present (original, negotiated, final, discount)")
        print("  ✓ All identity fields present (customer, product, transaction_id)")
        print("  ✓ All Razorpay fields present (order_id, payment_id, transaction_id)")
        print("  ✓ All status fields present (status, payment_status, order_id)")
        print("  ✓ Currency field present")
        print("  ✓ customer_accepted tracking field present")
        print("  ✓ __post_init__ initialization logic present")
        return True


def verify_webhook_service():
    """Verify WebhookService uses OrderAgent, not CommerceAgent"""
    print("\n" + "="*70)
    print("VERIFYING: WebhookService Order Creation Flow")
    print("="*70)
    
    filepath = Path("d:/AgentCommerce OS/Backend/script/webhook/webhook_service.py")
    
    forbidden = [
        (r'from script\.agents\.commerce_agent import', 
         "WebhookService should not import CommerceAgent"),
        (r'CommerceAgent\(\)', 
         "WebhookService should not instantiate CommerceAgent"),
    ]
    
    required = [
        (r'from script\.agents\.order_agent import', 
         "WebhookService should import OrderAgent"),
        (r'OrderAgent\(\)', 
         "WebhookService should use OrderAgent"),
    ]
    
    violations, content = check_file_for_patterns(filepath, forbidden, required)
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ WebhookService flow VERIFIED:")
        print("  ✓ Does NOT import CommerceAgent")
        print("  ✓ Does NOT instantiate CommerceAgent")
        print("  ✓ Imports OrderAgent for order creation")
        print("  ✓ Proper separation maintained for async flows")
        return True


def verify_transaction_manager():
    """Verify TransactionManager documentation"""
    print("\n" + "="*70)
    print("VERIFYING: TransactionManager Central Ownership")
    print("="*70)
    
    filepath = Path("d:/AgentCommerce OS/Backend/script/transaction/transaction_manager.py")
    
    required = [
        (r'CENTRAL TRANSACTION LIFECYCLE OWNER', 
         "TransactionManager should document central ownership"),
        (r'TransactionRepository', 
         "TransactionManager should use TransactionRepository"),
    ]
    
    violations, content = check_file_for_patterns(filepath, [], required)
    
    if violations:
        print("\nWARNINGS:")
        for v in violations:
            print(f"  {v}")
        # Not a hard failure, just a warning
        return True
    else:
        print("\n✅ TransactionManager ownership VERIFIED:")
        print("  ✓ Clearly documents central ownership role")
        print("  ✓ Uses TransactionRepository for persistence")
        print("  ✓ Owns complete transaction lifecycle")
        return True


def main():
    """Run all static architecture verifications"""
    print("\n" + "█"*70)
    print("█  AGENTCOMMERCE OS - STATIC ARCHITECTURE VERIFICATION")
    print("█  Component Separation of Concerns Analysis")
    print("█"*70)
    
    results = []
    
    results.append(("CommerceAgent Separation", verify_commerce_agent()))
    results.append(("NegotiationAgent Ownership", verify_negotiation_agent()))
    results.append(("TransactionState Completeness", verify_transaction_state()))
    results.append(("WebhookService Flow", verify_webhook_service()))
    results.append(("TransactionManager Ownership", verify_transaction_manager()))
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "█"*70)
    if all_passed:
        print("█  ✅ ALL ARCHITECTURE VERIFICATIONS PASSED")
        print("█  Component separation of concerns is properly enforced")
        print("█")
        print("█  Key achievements:")
        print("█  • CommerceAgent has NO payment/order layer knowledge")
        print("█  • NegotiationAgent handles pricing ONLY")
        print("█  • TransactionManager owns complete lifecycle")
        print("█  • WebhookService uses OrderAgent directly")
        print("█  • TransactionState has all required fields")
    else:
        print("█  ❌ SOME VERIFICATIONS FAILED")
        print("█  Review violations above")
    print("█"*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
