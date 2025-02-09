prompt = {
    "text": """
You're a Python unit tester. Given the use_case_details. and business_logic_code, develop python unit tests. Use monkeypatch to patch any external dependencies.

<use_case_details>
{{use_case_details}}
</use_case_details>

<business_logic_code>
{{business_logic_code}}
</business_logic_code>

Output only the tdd code without additional narrative.

<tdd_code>
""",
    "stop_seqs": ["</tdd_code>"],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 1,
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
}
