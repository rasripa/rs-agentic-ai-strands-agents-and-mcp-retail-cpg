"""
Lab 8 - Part 2: Policy Use Cases

This script demonstrates two production-critical policy patterns:
1. Restricting tool access based on Cognito user job role (JWT claims)
2. Enforcing validation rules on request payloads

Each Cedar policy is created as a separate API call (one statement per policy).
"""

import boto3
import json

region = boto3.Session().region_name
client = boto3.client('bedrock-agentcore-control', region_name=region)
ssm = boto3.client('ssm', region_name=region)

# Retrieve values stored by Part 1 (guardrails_in_policy.py)
policy_engine_id = ssm.get_parameter(Name='anycomp_policy_engine_id')['Parameter']['Value']
gateway_arn = ssm.get_parameter(Name='anycomp_agcore_gw_arn')['Parameter']['Value']

print("=" * 60)
print("Lab 8 - Part 2: Policy Use Cases")
print("=" * 60)
print(f"Policy Engine ID: {policy_engine_id}")
print(f"Gateway ARN: {gateway_arn}")


def create_policy_safe(name, description, statement):
    """Create a policy, skip if already exists."""
    try:
        response = client.create_policy(
            policyEngineId=policy_engine_id,
            name=name,
            description=description,
            validationMode='IGNORE_ALL_FINDINGS',
            definition={
                'cedar': {
                    'statement': statement
                }
            }
        )
        print(f"  ✅ Created: {name} ({response['policyId']})")
        return response['policyId']
    except client.exceptions.ConflictException:
        print(f"  ✅ Already exists: {name}")
        return None
    except Exception as e:
        print(f"  ❌ Error creating {name}: {e}")
        return None


# ============================================================
# Use Case 1: Role-Based Tool Access Control
# ============================================================
print("\n" + "=" * 60)
print("Use Case 1: Role-Based Tool Access (Cognito JWT)")
print("=" * 60)
print("""
  Scenario: Different employees have different tool permissions:
  • Customer Service → product search + inventory check
  • Warehouse Staff  → inventory check only (NO product search)
  • Managers         → all tools
""")

# Policy 1: Customer Service can search products and check inventory
policy_cs = f"""permit (
  principal is AgentCore::OAuthUser,
  action in [
    AgentCore::Action::"ProductSearchTarget___search_products",
    AgentCore::Action::"InventoryTarget___check_inventory"
  ],
  resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
  principal.hasTag("custom:job_role") &&
  principal.getTag("custom:job_role") == "customer_service"
}};"""

create_policy_safe(
    'RolePermit_CustomerService',
    'Customer Service can search products and check inventory',
    policy_cs
)

# Policy 2: Warehouse Staff can ONLY check inventory
policy_warehouse = f"""permit (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"InventoryTarget___check_inventory",
  resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
  principal.hasTag("custom:job_role") &&
  principal.getTag("custom:job_role") == "warehouse"
}};"""

create_policy_safe(
    'RolePermit_Warehouse',
    'Warehouse Staff can only check inventory',
    policy_warehouse
)

# Policy 3: Warehouse Staff are explicitly FORBIDDEN from product search
policy_warehouse_deny = f"""forbid (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"ProductSearchTarget___search_products",
  resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
  principal.hasTag("custom:job_role") &&
  principal.getTag("custom:job_role") == "warehouse"
}};"""

create_policy_safe(
    'RoleForbid_WarehouseNoSearch',
    'Warehouse Staff forbidden from product search',
    policy_warehouse_deny
)

# Policy 4: Managers can access all tools
policy_manager = f"""permit (
  principal is AgentCore::OAuthUser,
  action,
  resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
  principal.hasTag("custom:job_role") &&
  principal.getTag("custom:job_role") == "manager"
}};"""

create_policy_safe(
    'RolePermit_Manager',
    'Managers can access all tools',
    policy_manager
)

print("\n  Policy breakdown:")
print("  ┌─────────────────────────┬──────────────────┬─────────────────────┐")
print("  │ Role                    │ Product Search   │ Inventory Check     │")
print("  ├─────────────────────────┼──────────────────┼─────────────────────┤")
print("  │ customer_service        │ ✅ ALLOWED       │ ✅ ALLOWED          │")
print("  │ warehouse               │ 🚫 FORBIDDEN    │ ✅ ALLOWED          │")
print("  │ manager                 │ ✅ ALLOWED       │ ✅ ALLOWED          │")
print("  └─────────────────────────┴──────────────────┴─────────────────────┘")

# ============================================================
# Use Case 2: Request Payload Enforcement
# ============================================================
print("\n" + "=" * 60)
print("Use Case 2: Request Payload Enforcement")
print("=" * 60)
print("""
  Scenario: Validate tool arguments at the gateway:
  • Refund > $500 → DENIED unless manager
  • Invalid category → DENIED
  • Bad product ID format → DENIED
""")

# Policy 5: Limit refund amounts to $500 for non-managers
policy_refund = f"""forbid (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
  context.input has amount &&
  context.input.amount > 500
}}
unless {{
  principal.hasTag("custom:job_role") &&
  principal.getTag("custom:job_role") == "manager"
}};"""

create_policy_safe(
    'PayloadForbid_RefundLimit',
    'Limit refund amounts to $500 for non-managers',
    policy_refund
)

# Policy 6: Product search must include a valid category
policy_category = f"""forbid (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"ProductSearchTarget___search_products",
  resource == AgentCore::Gateway::"{gateway_arn}"
)
unless {{
  context.input has category &&
  (context.input.category == "Clothing" ||
   context.input.category == "Footwear" ||
   context.input.category == "Accessories" ||
   context.input.category == "Outerwear")
}};"""

create_policy_safe(
    'PayloadForbid_ValidCategory',
    'Product search must include a valid category',
    policy_category
)

# Policy 7: Inventory checks must have properly formatted product ID
policy_product_id = f"""forbid (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"InventoryTarget___check_inventory",
  resource == AgentCore::Gateway::"{gateway_arn}"
)
unless {{
  context.input has product_id &&
  context.input.product_id like "PROD-*"
}};"""

create_policy_safe(
    'PayloadForbid_ValidProductId',
    'Inventory checks must have PROD-* format product ID',
    policy_product_id
)

print("\n  Payload enforcement rules:")
print("  ┌─────────────────────────┬────────────────────────────────────────────┐")
print("  │ Rule                    │ Behavior                                   │")
print("  ├─────────────────────────┼────────────────────────────────────────────┤")
print("  │ Refund > $500           │ DENIED unless role == 'manager'            │")
print("  │ Invalid category        │ DENIED (must be Clothing/Footwear/etc.)    │")
print("  │ Bad product ID format   │ DENIED (must match 'PROD-*')              │")
print("  └─────────────────────────┴────────────────────────────────────────────┘")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("✅ Lab 8 Part 2 Complete!")
print("=" * 60)
print("""
Policies created:
  Use Case 1 (Role-Based Access):
    • RolePermit_CustomerService   - CS can search + inventory
    • RolePermit_Warehouse         - Warehouse can inventory only
    • RoleForbid_WarehouseNoSearch  - Warehouse blocked from search
    • RolePermit_Manager           - Managers get all tools

  Use Case 2 (Payload Enforcement):
    • PayloadForbid_RefundLimit    - Refunds > $500 need manager
    • PayloadForbid_ValidCategory  - Must use valid categories
    • PayloadForbid_ValidProductId - Product ID must be PROD-*

Key Cedar concepts used:
  • principal.hasTag() / principal.getTag() - Read JWT claims
  • context.input has <field>              - Check field exists
  • context.input.<field> like 'PROD-*'    - Pattern matching
  • unless { ... }                         - Exception clause
  • forbid always wins over permit
""")
