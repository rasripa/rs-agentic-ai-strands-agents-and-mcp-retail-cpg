"""
Lab 8 - Test: Cedar Policy Enforcement Demo

This script demonstrates how Cedar authorization policies control
tool access at the gateway. Run this AFTER policy_use_cases.py.

It simulates how the policy engine would evaluate requests from
different user roles and with different payload arguments, showing
the expected ALLOW/DENY decisions based on the policies you created.

Note: Since we can't mint real Cognito JWTs in this demo, we show
the policy logic by listing all policies and explaining the expected
behavior for each scenario. For gateways configured with CUSTOM_JWT,
the policy engine automatically extracts JWT claims as principal tags.
"""

import boto3
import json

region = boto3.Session().region_name
client = boto3.client('bedrock-agentcore-control', region_name=region)
ssm = boto3.client('ssm', region_name=region)

policy_engine_id = ssm.get_parameter(Name='anycomp_policy_engine_id')['Parameter']['Value']
gateway_arn = ssm.get_parameter(Name='anycomp_agcore_gw_arn')['Parameter']['Value']

print("=" * 60)
print("TEST: Cedar Policy Enforcement Scenarios")
print("=" * 60)
print(f"Policy Engine: {policy_engine_id}")
print(f"Gateway: {gateway_arn}")

# ============================================================
# List all policies in the engine
# ============================================================
print("\n" + "=" * 60)
print("Active Policies in Engine")
print("=" * 60)

policies_response = client.list_policies(policyEngineId=policy_engine_id)

# Try common response keys
policies = (
    policies_response.get('items', []) or
    policies_response.get('policies', []) or
    policies_response.get('policyList', [])
)

# If still empty, show all keys for debugging
if not policies:
    # Try to find the list in any key that contains a list
    for key, value in policies_response.items():
        if isinstance(value, list) and len(value) > 0:
            policies = value
            break

for p in policies:
    name = p.get('name', p.get('policyName', 'unnamed'))
    pid = p.get('policyId', p.get('id', ''))
    print(f"  • {name} ({pid})")

print(f"\n  Total: {len(policies)} policies")

# ============================================================
# Scenario walkthrough
# ============================================================
print("\n" + "=" * 60)
print("Scenario 1: Customer Service user searches for products")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "customer_service"
  Action:    ProductSearchTarget___search_products
  Payload:   {{"query": "summer dresses", "category": "Clothing"}}

  Policy evaluation:
    ✅ RolePermit_CustomerService → PERMIT (role matches)
    ✅ PayloadForbid_ValidCategory → does NOT forbid (category = "Clothing")
    
  Result: ✅ ALLOWED
  
  The customer service rep can search for products because:
  1. Their role is explicitly permitted for product search
  2. They provided a valid category ("Clothing")
""")

print("=" * 60)
print("Scenario 2: Warehouse user tries to search products")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "warehouse"
  Action:    ProductSearchTarget___search_products
  Payload:   {{"query": "check stock levels", "category": "Clothing"}}

  Policy evaluation:
    🚫 RoleForbid_WarehouseNoSearch → FORBID (role is warehouse)
    
  Result: 🚫 DENIED (forbid always wins, even if other permits match)
  
  The warehouse user cannot search products because there is an
  explicit forbid policy. Remember: forbid ALWAYS wins over permit.
""")

print("=" * 60)
print("Scenario 3: Warehouse user checks inventory")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "warehouse"
  Action:    InventoryTarget___check_inventory
  Payload:   {{"product_id": "PROD-048"}}

  Policy evaluation:
    ✅ RolePermit_Warehouse → PERMIT (role matches for inventory)
    ✅ PayloadForbid_ValidProductId → does NOT forbid (PROD-048 matches "PROD-*")
    
  Result: ✅ ALLOWED
  
  The warehouse user can check inventory because:
  1. Their role is permitted for inventory checks
  2. The product ID matches the required format "PROD-*"
""")

print("=" * 60)
print("Scenario 4: Warehouse user uses invalid product ID")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "warehouse"
  Action:    InventoryTarget___check_inventory
  Payload:   {{"product_id": "SKU-12345"}}

  Policy evaluation:
    ✅ RolePermit_Warehouse → PERMIT (role matches)
    🚫 PayloadForbid_ValidProductId → FORBID (SKU-12345 doesn't match "PROD-*")
    
  Result: 🚫 DENIED
  
  Even though the warehouse user is permitted for inventory checks,
  the payload validation policy blocks the request because the
  product_id doesn't match the required format.
""")

print("=" * 60)
print("Scenario 5: Customer Service rep tries $750 refund")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "customer_service"
  Action:    RefundTarget___process_refund
  Payload:   {{"orderId": "ORD-789", "amount": 750, "reason": "customer request"}}

  Policy evaluation:
    🚫 PayloadForbid_RefundLimit → FORBID
       (amount 750 > 500 AND role is NOT "manager")
    
  Result: 🚫 DENIED
  
  The refund is blocked because:
  1. Amount exceeds $500
  2. The user is not a manager (the 'unless' clause doesn't apply)
""")

print("=" * 60)
print("Scenario 6: Manager processes $750 refund")
print("=" * 60)
print("""
  Principal: OAuthUser with custom:job_role = "manager"
  Action:    RefundTarget___process_refund
  Payload:   {{"orderId": "ORD-789", "amount": 750, "reason": "VIP escalation"}}

  Policy evaluation:
    ✅ RolePermit_Manager → PERMIT (managers get all tools)
    ✅ PayloadForbid_RefundLimit → does NOT forbid
       (amount > 500 BUT role IS "manager" → unless clause applies)
    
  Result: ✅ ALLOWED
  
  The manager can process the high-value refund because:
  1. Their role permits all actions
  2. The 'unless' clause in the refund policy exempts managers
""")

# ============================================================
# Authorization semantics recap
# ============================================================
print("=" * 60)
print("Cedar Authorization Semantics")
print("=" * 60)
print("""
  How the policy engine decides:
  
  ┌─────────────────────────────────────────────────┐
  │ Request arrives at gateway                       │
  │         ↓                                        │
  │ Collect all matching policies                    │
  │         ↓                                        │
  │ If ANY forbid matches → 🚫 DENY                 │
  │   (forbid ALWAYS wins, no exceptions)            │
  │         ↓                                        │
  │ If at least one permit matches → ✅ ALLOW        │
  │         ↓                                        │
  │ If no permit matches → 🚫 DENY (default deny)   │
  └─────────────────────────────────────────────────┘
  
  Key rules:
  • Default deny: no permit = denied
  • Forbid wins: forbid overrides any permit
  • unless: inverts the forbid (exempts specific cases)
  • when: adds conditions to permit/forbid
  
  This means you can layer policies:
  • Broad permit for a role + specific forbids for edge cases
  • Broad forbid + unless for exemptions
""")

print("\n✅ Test scenarios complete!")
print("   These scenarios show exactly how the policy engine")
print("   evaluates real requests against your Cedar policies.")
