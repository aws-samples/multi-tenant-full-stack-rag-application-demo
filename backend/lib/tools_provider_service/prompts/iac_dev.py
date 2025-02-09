prompt = {
    "text": """You're an experienced AWS developer. Given the use_case_details, architecture_plan, and business_logic_code, provide YAML CloudFormation templates to deploy the stack. 

Workflow:
- Make sure to encapsulate the entire business logic into the CloudFormation template so that it's ready to deploy. 
- Never use resource names unless they're required by the CloudFormation API. 
- Make sure you give any functions the permissions they need to execute, including creation of CloudWatch Log Groups.

<use_case_details>
{{use_case_details}}
</use_case_details>

<architecture_plan>
{{architecture_plan}}
</architecture_plan>

<business_logic_code>
{{business_logic_code}}
</business_logic_code>

Now output CloudFormation YAML code without additional narration:

<cloudformation_yaml_code>
""",
    "stop_seqs": ["</cloudformation_yaml_code>"],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 1,
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
}