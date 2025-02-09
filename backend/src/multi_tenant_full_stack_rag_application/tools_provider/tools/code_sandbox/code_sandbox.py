import boto3
import os
import requests
import subprocess
import time
import zipfile 

from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider import ToolProvider
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_runner_event import CodeSandboxRunnerEvent
import json
# from threading import Thread


cstv2 = None
print("Initializing code_sandbox.")
print(f"AWS_LAMBDA_RUNTIME_API: {os.getenv('AWS_LAMBDA_RUNTIME_API')}")


class CodeSandbox(ToolProvider):
    def __init__(self):
        super().__init__()
        self.sandbox_host = os.getenv('CODE_SANDBOX_HOST')
        # all functions created must start with the prefix below 
        # self.guru = boto3.client('codeguru-security')
        # self.s3 = boto3.client('s3')
        print("sandbox tool initialized")

    
    @staticmethod
    def get_inputs():
        return {
            "comment": "Either iac_code is required or business_logic_code is required. tdd_code is optional.",
            "business_logic_code": {
                "required": "Either business_logic_code is required or iac_code. It's OK if both are sent.",
                "type": "string",
                "description": "The business logic code.",
            },
            "iac_code": {
                "required": "Either business_logic_code is required or iac_code.",
                "type": "string",
                "description": "The infrastructure code.",
            },
            "tdd_code": {
                "required": "Optional",
                "type": "string",
                "description": "The tdd code to run to tdd the business_logic_code. Always the same language as the business logic code."
            }
        }

    @staticmethod
    def get_outputs():
        return {
            "results": {
                "build": {
                    "stderr": "the error output from the docker build for the container.",
                    "stdout": "the standard output from the docker build for the container.",
                    "exit_code": "exit code from the docker build"
                },
                "tdd": {
                    "stderr": "the error output from the docker run for the container.",
                    "stdout": "the standard output from the docker run for the container.",
                    "exit_code": "exit code from the docker run"
                },
            }
        }

    def handler(self, evt):
        print(f"CodeSandboxRunner received Lambda event {evt}")
        handler_evt = CodeSandboxRunnerEvent(**evt)
        print(f"CodeSandboxRunnerEvent is now {handler_evt.__dict__}")
        result = self.run_tool(handler_evt)
        result['business_logic_code'] = handler_evt.business_logic_code
        result['iac_code'] = handler_evt.iac_code
        result['tdd_code'] = handler_evt.tdd_code
        
        return result

    def run_tool(self, event):
        url = f"http://{self.sandbox_host}:8000/sandbox"
        print(f"Calling sandbox at {url} with event {event.__dict__}")
        response = requests.post(url, json=event.__dict__)
        print(f"Got response from sandbox: {response.__dict__}")
        return response.json()


def handler(evt, ctx):
    global cstv2
    print(f"code_sandbox.handler got event {evt}")
    orig_evt = evt.copy()

    if not cstv2:
        cstv2 = CodeSandboxRunner()
    if 'node' in evt and 'inputs' in evt['node']:
        # this came from a bedrock prompt flow so the format
        # is a little different than in this stack. Modify
        # it a bit before passing it on.
        evt = {}
        for input_dict in orig_evt['node']['inputs']:
            evt[input_dict['name']] = input_dict['value']

    return cstv2.handler(evt)
