import boto3
import argparse
from strands import Agent, tool
from strands_tools import retrieve
from strands.models import BedrockModel

region = boto3.Session().region_name

# Initialize SSM client
ssm_client = boto3.client('ssm', region_name=region)

prod_search_kb_id = ssm_client.get_parameter(Name="product_search_kb_id")['Parameter']['Value']
print(f"Product search KB ID is {prod_search_kb_id}")

agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
print(f"Agent Model ID is {agent_model_id}")

# Define the tool to fetch data from the product knowledge base
@tool
def get_products_from_kb(user_query: str) -> str:
    """
    Use this tool when you need to search for products 
    in the Knowledge Base that match user's product search query.

    Args:
        user_query: The user's product search query

    """    
    try:        
        # Use strands retrieve tool
        tool_use = {
            "toolUseId": "get_products_from_kb",
            "input": {
                "text": user_query,
                "knowledgeBaseId": prod_search_kb_id,
                "region": region,
                "numberOfResults": 5,
                "score": 0.4
            }
        }
        result = retrieve.retrieve(tool_use)

        if result["status"] == "success":
            return result["content"][0]["text"]
        else:
            return f"Unable to access technical support documentation. Error: {result['content'][0]['text']}"

    except Exception as e:
        print(f"Detailed error in get_anycompany_docs: {str(e)}")
        return f"Unable to access anycompany documentation. Error: {str(e)}"



# Define the system prompt for the AI shopping assistant
_system_prompt = """
You are an AI shopping assistant that helps customers discover products and reviews. 
You have access to:
1. A tool for searching products that match with user's product search query

When a customer asks about products:
1. First, search the knowledge base for relevant products using the search_products tool
2. Provide helpful recommendations based on the information gathered
3. Always format responses in a clear, customer-friendly manner
4. Include relevant product details like price, features, and availability when available

Guidelines:
- Be helpful, accurate, and informative
- Provide structured responses when possible
- If you cannot find specific information, clearly state this
- Always prioritize customer needs and preferences
- Suggest alternatives when the exact request cannot be fulfilled
- Include review summaries and ratings when available

Response Format:
- Start with a brief summary of findings
- List recommended products with key in the below JSON array format -
[
   { "product_id": "PROD-010", 
     "product_name": "Uniqlo Ultra Light Down Jacket", 
     "brand_name": "Uniqlo", 
     "category": "Clothing", 
     "subcategory": "Outerwear", 
     "gender": "Unisex", 
     "price": 69.90, 
     "sale_price": 49.90, 
     "size": ["XS", "S", "M", "L", "XL", "XXL"], 
     "color": ["Black", "Navy", "Red", "Olive", "Grey"], 
     "materials": ["100% Nylon", "Down filling", "Water-repellent coating"], 
     "season": "Fall/Winter"
     },
     ...
]
"""

# Create a Bedrock guardrail
bedrock_client = boto3.client('bedrock')

def create_guardrail():
    guardrail_name = 'product-specific-restrictions'
    
    # First, check if a guardrail with this name already exists
    try:
        # List existing guardrails
        list_response = bedrock_client.list_guardrails()
        
        # Check if our guardrail already exists
        for guardrail in list_response.get('guardrails', []):
            if guardrail.get('name') == guardrail_name:
                guardrail_id = guardrail.get('id')
                guardrail_version = "DRAFT"
                print(f"Found existing guardrail: {guardrail_name}")
                print("Guardrail ID:", guardrail_id)
                print("Guardrail ARN:", guardrail.get('arn'))
                return guardrail_id, guardrail_version
                
    except Exception as e:
        print(f"Error checking existing guardrails: {str(e)}")
        # Continue to create new guardrail if listing fails
    
    # If guardrail doesn't exist, create a new one
    print(f"Creating new guardrail: {guardrail_name}")
    try:
        response = bedrock_client.create_guardrail(
            name=guardrail_name,
            description='Prevents the model from providing recommendations on specific products.',
            topicPolicyConfig={
                'topicsConfig': [
                    {
                        'name': 'Product restrictions',
                        'definition': 'Providing recommendations on product restricted by anycompany and not related to the products available in anycompany.',
                        'examples': ['Competitor brands', 'Inappropriate or offensive clothing', 'fake','counterfeit'
                        ],
                        'type': 'DENY'
                    }
                ]
            },
            contentPolicyConfig={
                'filtersConfig': [
                    {
                        'type': 'SEXUAL',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'HIGH'
                    },
                    {
                        'type': 'VIOLENCE',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'HIGH'
                    },
                    {
                        'type': 'HATE',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'HIGH'
                    },
                    {
                        'type': 'INSULTS',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'HIGH'
                    },
                    {
                        'type': 'MISCONDUCT',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'HIGH'
                    },
                    {
                        'type': 'PROMPT_ATTACK',
                        'inputStrength': 'HIGH',
                        'outputStrength': 'NONE'
                    }
                ]
            },
            wordPolicyConfig={
                'wordsConfig': [
                    {'text': 'counterfeit'},
                    {'text': 'fake'},
                    {'text': 'sexy'},
                    {'text': 'h&m'},
                    {'text': 'nazi'},
                    {'text': 'lolita'},
                    {'text': 'dupe'}
                ],
                'managedWordListsConfig': [
                    {
                        'type': 'PROFANITY'
                    }
                ]
            },
            blockedInputMessaging='Dear customer, I apologize, but I am not able to provide any recommendations related to your request. Please modify your input and try again.',
            blockedOutputsMessaging='Dear customer, I apologize, but I am not able to provide any recommendations related to your request. Please modify your input and try again.',
        )

        guardrail_id = response.get('guardrailId')
        guardrail_version = "DRAFT"

        # Print the response to get the guardrail ID
        print("Guardrail ID:", guardrail_id)
        print("Guardrail ARN:", response.get('guardrailArn'))
        
        return guardrail_id, guardrail_version
        
    except Exception as e:
        print(f"Error creating guardrail: {str(e)}")
        raise



# Test function to check if input/output is blocked by guardrail
bedrock_runtime = boto3.client('bedrock-runtime')
def test_guardrail(guardrail_id, guardrail_version, text, source_type='INPUT'):
      print(f"Testing Guardrail for the input- '{text}'")
      response = bedrock_runtime.apply_guardrail(
          guardrailIdentifier=guardrail_id,
          guardrailVersion=guardrail_version,
          source=source_type,  # can be 'INPUT' or 'OUTPUT'
          content=[{"text": {"text": text}}]
      )

      # New response format uses different fields
      print(f"Action: {response.get('action')}")
      print(f"Action Reason: {response.get('actionReason', 'None')}")

      # Check if content was blocked
      is_blocked = response.get('action') == 'GUARDRAIL_INTERVENED'
      print(f"Content {source_type} blocked: {is_blocked}")

      if is_blocked:
          # Print topic policies that were triggered
          assessments = response.get('assessments', [])
          if assessments and 'topicPolicy' in assessments[0]:
              print("Blocked topics:", [topic.get('name') for topic in
          assessments[0]['topicPolicy'].get('topics', [])
                                       if topic.get('action') == 'BLOCKED'])

          # Print the modified output if available
          if 'outputs' in response and response['outputs']:
              print("Modified content:", response['outputs'][0].get('text', 'None'))

      return response


# Helper function to test the agent and check for guardrail interventions
def test_agent_with_guardrail(guardrail_id, guardrail_version, prompt):
    print(f"Testing Agent with Guardrail for the input - '{prompt}'")
    # Create a Bedrock model with guardrail configuration
    bedrock_model = BedrockModel(
        model_id=agent_model_id,
        region_name=region,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
        guardrail_trace="enabled",
        temperature=0.3
    )

    # Create agent with the guardrail-protected model
    product_search_agent_with_guardrail = Agent(
        system_prompt=_system_prompt,
        model=bedrock_model,
        tools=[get_products_from_kb]
    )

    # Get agent response
    response = product_search_agent_with_guardrail(prompt)

    # Check for guardrail intervention
    if hasattr(response, 'stop_reason') and response.stop_reason == "guardrail_intervened":
        print("\n ⚠️ GUARDRAIL INTERVENED!")
        #print(f"Response: {response}")
    else:
        return response


def main():

    ######################################
    # Create the Bedrock Guardrail
    guardrail_id, guardrail_version = create_guardrail()

    # Test Bedrock Guardrail directly
    # Test input that will be blocked. This will be blocked since the input contains the word "lolita".
    print("\n-------Test 1------------------------")
    print("Testing input that will be blocked:")
    test_guardrail(guardrail_id, guardrail_version, "Can you recommend me a dress lolita style?")

    print("\n-------Test 2------------------------")
    # Test input that will be blocked. This will be blocked since the input contains the word "dupe".
    print("\nTesting input that will be blocked:")
    test_guardrail(guardrail_id, guardrail_version, "Where can I find a dupe of Chanel jacket?")

    # Test some safe input. This will not be blocked.
    print()
    print("\n-------Test 3------------------------")
    print("Testing safe input:")
    test_guardrail(guardrail_id, guardrail_version, "I am looking for a swimming suit for my holidays in Bali. What can you recommend? I want a 2 pieces")

    ##################################################
    # Now test an Agent that has a Guardrail
    # Test with a safe question 
    print("\n-------Test 4------------------------")
    test_agent_with_guardrail(guardrail_id, guardrail_version, "What colors are available for pants?")

    print()
    print("\n-------Test 5------------------------")
    # Test with a question that asks about hate recommendation. This will get blocked.
    test_agent_with_guardrail(guardrail_id, guardrail_version, "Find me a t-shirt with the nazi symbol on it")

if __name__ == "__main__":
    main()
