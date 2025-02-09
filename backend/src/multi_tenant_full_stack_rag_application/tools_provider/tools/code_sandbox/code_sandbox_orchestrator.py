import boto3
import os
import requests
import subprocess
import time
import zipfile 

from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_orchestrator_event import CodeSandboxOrchestratorEvent
from multi_tenant_full_stack_rag_application import utils

import json


cso = None
print("Initializing code_sandbox orchestrator.")


class CodeSandboxOrchestrator:
    def __init__(self):
        super().__init__()
        print("sandbox orchestrator tool initialized")
        stack_name = os.getenv('STACK_NAME')
        self.bra = boto3.client('bedrock-agent')
        prompt_ids = json.loads(os.getenv('PROMPTS'))
        self.prompts = {}
        for prompt_name in prompt_ids:
            prompt_id = prompt_ids[prompt_name]
            prompt = utils.get_prompt(prompt_id)
            prompts[prompt_name] = {
                "id": prompt_id,
                "text": prompt['text']
            }
    @staticmethod
    def get_inputs():
        return {
            "next_loop_instructions": {
                "type": "string",
                "description": "The instructions from the orchestration model to be used as guidance for the next iteration of the loop.",
            },
            "do_architecture": {
                "type": "boolean",
                "description": "Whether or not the architecture code needs to be redone."
            },
            "do_business_logic": {
                "type": "string",
                "description": "Whether or not the business logic code needs to be redone."
            },
            "do_iacc": {
                "type": "string",
                "description": "Whether or not the iac code needs to be redone."
            },
            "do_tdd": {
                "type": "string",
                "description": "Whether or not the tdd code needs to be redone."
            },
            "web_search_query": {
                "type": "string",
                "description": "The query string to use (only if needed) for searching for troubleshooting info online. As the orchestration model, if you know what to do next without looking up extra information, then don't use this."
            },
            "web_search_top_x": {
                "type": "string",
                "description": "the number of search results to return. 0 if no search is needed."
            }
        }

    @staticmethod
    def get_outputs():
        return {
            "comment": "this orchestrator runs the web search, if needed, and then one or more of the developer prompts (business, iac, or tdd). It returns an object with a statusCode and an HTTP status code upon completion, and nothing else.",
            "statusCode": {
                "type": "number",
                "description": "the http status code number"
            }
        }

    def handler(self, evt):
        print(f"CodeSandboxOrchestrator received Lambda event {evt}")
        handler_evt = CodeSandboxOrchestratorEvent(**evt)
        print(f"CodeSandboxOrchestratorEvent is now {handler_evt.__dict__}")
        
        if handler_evt.web_search_query != '' and \
            handler_evt.web_search_top_x > 0:
            web_context = self.run_web_search(
                handler_evt.web_search_query, 
                handler_evt.web_search_top_x
            )
        return result

    def run_architect(self, context):
        print(f"running architect with context {self.prompts['architect']}")

    def run_web_search(self, query, top_x):
        print(f"running web search for {query} with top_x {top_x}")
        fn_name = utils.get_ssm_params('tools_provider_function_name')
        print(f"fn_name {fn_name}")
        response = utils.invoke_lambda(
            fn_name,
            {
                'operation': 'invoke_tool',
                'origin': utils.get_ssm_params('origin_tools_provider'),
                'args': {
                    "operation": "SEARCH_AND_DOWNLOAD",
                    "search_query": query,
                    "tool_name": "web_search_tool",
                    "top_x": top_x
                }
            }
        )
        if 'errorMessage' in response.keys():
            raise Exception(response['errorMessage'])
        
        print(f"web search response {response}")
        return response


def handler(evt, ctx):
    global cstv2
    print(f"code_sandbox.handler got event {evt}")
    orig_evt = evt.copy()

    if not cstv2:
        cstv2 = CodeSandboxOrchestrator()
    if 'node' in evt and 'inputs' in evt['node']:
        # this came from a bedrock prompt flow so the format
        # is a little different than in this stack. Modify
        # it a bit before passing it on.
        evt = {}
        for input_dict in orig_evt['node']['inputs']:
            evt[input_dict['name']] = input_dict['value']

    return cstv2.handler(evt)
