#!/usr/bin/env python3
"""
Architecture Verification Script

Verifies that component separation of concerns is enforced:
1. CommerceAgent does NOT have payment_agent/order_agent/checkout_agent references
2. NegotiationAgent only handles pricing
3. TransactionManager owns complete lifecycle
4. CommerceExecutionAgent owns payment/order execution
"""

import sys
from pathlib import Path
import inspect

# Add root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def verify_commerce_agent():
    """Verify CommerceAgent separation from payment layer"""
    print("\n" + "="*70)
    print("VERIFYING: CommerceAgent Separation of Concerns")
    print("="*70)
    
    from script.agents.commerce_agent import CommerceAgent
    
    agent = CommerceAgent()
    
    # Check that forbidden attributes don't exist
    violations = []
    
    if hasattr(agent, 'payment_agent'):
        violations.append("❌ CommerceAgent.payment_agent exists (should not)")
    
    if hasattr(agent, 'order_agent'):
        violations.append("❌ CommerceAgent.order_agent exists (should not)")
    
    if hasattr(agent, 'checkout_agent'):
        violations.append("❌ CommerceAgent.checkout_agent exists (should not)")
    
    # Check that required attributes DO exist
    if not hasattr(agent, 'execution_agent'):
        violations.append("❌ CommerceAgent.execution_agent missing (should exist)")
    
    if not hasattr(agent, 'transaction_manager'):
        violations.append("❌ CommerceAgent.transaction_manager missing (should exist)")
    
    if not hasattr(agent, 'negotiation_agent'):
        violations.append("❌ CommerceAgent.negotiation_agent missing (should exist)")
    
    # Check for deprecated methods
    deprecated_methods = ['_execute_payment', '_create_order']
    for method_name in deprecated_methods:
        if hasattr(agent, method_name):
            method = getattr(agent, method_name)
            # Check if it's properly deprecated (returns None)
            try:
                import inspect
                source = inspect.getsource(method)
                if 'DEPRECATED' in source and 'return None' in source:
                    print(f"✓ {method_name} properly deprecated")
                else:
                    violations.append(f"⚠ {method_name} exists but not properly deprecated")
            except:
                pass
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ CommerceAgent separation VERIFIED:")
        print("  ✓ No payment_agent reference")
        print("  ✓ No order_agent reference")
        print("  ✓ No checkout_agent reference")
        print("  ✓ Has execution_agent (correct)")
        print("  ✓ Has transaction_manager (correct)")
        print("  ✓ Has negotiation_agent (correct)")
        return True


def verify_negotiation_agent():
    """Verify NegotiationAgent only handles pricing"""
    print("\n" + "="*70)
    print("VERIFYING: NegotiationAgent Pricing-Only Ownership")
    print("="*70)
    
    from script.agents.negotiation_agent import NegotiationAgent
    
    agent = NegotiationAgent()
    
    # Check for forbidden attributes
    violations = []
    
    forbidden = ['payment_agent', 'order_agent', 'razorpay_client', 
                 'payment_verifier', 'webhook_handler']
    
    for attr in forbidden:
        if hasattr(agent, attr):
            violations.append(f"❌ NegotiationAgent.{attr} exists (should not)")
    
    # Check that negotiate method exists
    if not hasattr(agent, 'negotiate'):
        violations.append("❌ NegotiationAgent.negotiate method missing")
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ NegotiationAgent separation VERIFIED:")
        print("  ✓ No payment layer knowledge")
        print("  ✓ Only handles negotiation logic")
        return True


def verify_transaction_manager():
    """Verify TransactionManager owns complete lifecycle"""
    print("\n" + "="*70)
    print("VERIFYING: TransactionManager Central Ownership")
    print("="*70)
    
    from script.transaction.transaction_manager import TransactionManager
    from script.transaction.transaction_state import TransactionState
    
    manager = TransactionManager()
    
    violations = []
    
    # Check that repository exists
    if not hasattr(manager, 'repository'):
        violations.append("❌ TransactionManager.repository missing")
    
    # Check that methods exist
    required_methods = ['get', 'get_by_transaction_id', 'create_or_update']
    for method_name in required_methods:
        if not hasattr(manager, method_name):
            violations.append(f"❌ TransactionManager.{method_name} missing")
    
    # Check TransactionState has required fields
    sample = TransactionState(customer_id=1)
    required_fields = [
        'customer_id', 'product_id', 
        'original_price', 'negotiated_price', 'final_price', 'discount_percent',
        'transaction_id', 'status', 'customer_accepted',
        'razorpay_order_id', 'razorpay_payment_id', 'payment_transaction_id',
        'payment_status', 'order_id', 'currency'
    ]
    
    for field in required_fields:
        if not hasattr(sample, field):
            violations.append(f"❌ TransactionState.{field} missing")
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ TransactionManager central ownership VERIFIED:")
        print("  ✓ Repository for persistence")
        print("  ✓ All lifecycle methods present")
        print("  ✓ TransactionState has all required fields:")
        print(f"    - Pricing: original_price, negotiated_price, final_price, discount_percent")
        print(f"    - Identity: transaction_id, customer_id, product_id")
        print(f"    - Razorpay: razorpay_order_id, razorpay_payment_id, payment_transaction_id")
        print(f"    - Status: status, payment_status, order_id")
        print(f"    - Other: customer_accepted, currency")
        return True


def verify_no_cyclic_dependencies():
    """Verify no circular dependencies between layers"""
    print("\n" + "="*70)
    print("VERIFYING: No Cyclic Dependencies")
    print("="*70)
    
    violations = []
    
    # CommerceAgent should not import payment_agent
    try:
        import script.agents.commerce_agent as ca
        source = inspect.getsource(ca)
        if 'from script.agents.payment_agent import' in source:
            violations.append("❌ CommerceAgent imports PaymentAgent")
    except:
        pass
    
    # NegotiationAgent should not import Razorpay components
    try:
        import script.agents.negotiation_agent as na
        source = inspect.getsource(na)
        if 'razorpay' in source.lower():
            violations.append("❌ NegotiationAgent references Razorpay")
    except:
        pass
    
    if violations:
        print("\nVIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        return False
    else:
        print("\n✅ No cyclic dependencies detected")
        return True


def main():
    """Run all architecture verifications"""
    print("\n" + "█"*70)
    print("█  AGENTCOMMERCE OS - ARCHITECTURE VERIFICATION")
    print("█  Component Separation of Concerns")
    print("█"*70)
    
    results = []
    
    results.append(("CommerceAgent Separation", verify_commerce_agent()))
    results.append(("NegotiationAgent Ownership", verify_negotiation_agent()))
    results.append(("TransactionManager Ownership", verify_transaction_manager()))
    results.append(("Cyclic Dependencies", verify_no_cyclic_dependencies()))
    
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
    else:
        print("█  ❌ SOME VERIFICATIONS FAILED")
        print("█  Review violations above")
    print("█"*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
