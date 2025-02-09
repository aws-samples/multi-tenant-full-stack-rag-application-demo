prompt = {
    "text": """You're an experienced Python developer.
Using the list of json objects in the architecture_plan, evaluate each of the resources in the architecture output and write the Python busines logic required for the project. Don't do tdd or IAC code, just business logic. Not all resources in the architecture output will require business logic. Only handle business logic. Always assume credentials and authorization will be handled by IaC code.

<use_case_details>
{{use_case_details}}
</use_case_details>

<architecture_plan>
{{architecture_plan}}
</architecture_plan>

Don't provide narrative, just provide code_output.

<code_output>
""",
    "stop_seqs": ["</code_output>"],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 1,
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
}
