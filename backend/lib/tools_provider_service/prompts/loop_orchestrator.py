prompt = {
    "text": """You're orchestrating the loop plan for a looping code generation agent. You will receive the previous loop's business logic code, IaC code, tdd code, and the output from the previous tdd run, along with the loop plans for previous loops.
Your job is to select the business logic tool, the iac code tool, the tdd code tool, and optionally to look up extra information via a web search tool if you need to research a solution.

<use_case_details>
{{use_case_details}}
</use_case_details>

<previous_loop_results>
{{previous_results}}
</previous_loop_results>

<existing_business_logic_code>
{{business_logic_code}}
</existing_business_logic_code>

<existing_iac_code>
{{iac_code}}
</existing_iac_code>

<existing_tdd_code>
{{tdd_code}}
</existing_tdd_code>

<required_output_format>
{
    "web_search_query": {
        "type": "string",
        "description": "The query string to use (only if needed) for searching for troubleshooting info online. As the orchestration model, if you know what to do next without looking up extra information, then don't use this."
    },
    "web_search_top_x": {
        "type": "number",
        "description": "the number of search results to return. 0 if no search is needed."
    },
    "do_architecture": {
        "type": "boolean",
        "description": "whether to do the architecture on the next loop."
    },
    "do_business_logic": {
        "type": "boolean",
        "description": "whether to do the business logic on the next loop."
    },
    "do_iac": {
        "type": "boolean",
        "description": "whether to do the iac on the next loop."
    },
    "do_tdd": {
        "type": "boolean",
        "description": "whether to do the tdd code on the next loop."
    },
    "next_loop_instructions": {
        "type": "string",
        "description": "As the orchestration model, you should provide instructions for the next loop for the parts that need doing."
    }
}
</required_output_format>

Now return the required output as specified above, without further commentary.

<output>
""",
    "stop_seqs": ["</output>"],
    "max_tokens": 1000,
    "temperature": 0.5,
    "top_p": 1,
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
}
