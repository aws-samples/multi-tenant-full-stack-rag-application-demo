import pytest
import boto3
import json
import os
import sys

sys.path.insert(0, '../src')
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_orchestrator import CodeSandboxOrchestrator
from multi_tenant_full_stack_rag_application import utils

s3 = boto3.client('s3')

@pytest.fixture(scope="session")
def code_sandbox_orchestrator():
    return CodeSandboxOrchestrator()

def test_create_code_sandbox_tool(code_sandbox_orchestrator):
    assert isinstance(code_sandbox_orchestrator, CodeSandboxOrchestrator)

def test_run_web_search(code_sandbox_orchestrator):
    result = code_sandbox_orchestrator.run_web_search("what is the meaning to life, the universe, and everything?", 1)
    assert isinstance(result, dict)
    assert result['statusCode'] == '200'
    body = json.loads(result['body'])
    url = list(body.keys())[0]
    assert '42' in url
    assert 'Hitchhikers' in url
    print(result)

def test_run_architect(code_sandbox_orchestrator):
    result = code_sandbox_orchestrator.run_architect("Please create a hello world lambda function.")
    assert isinstance(result, dict)
    assert result['statusCode'] == '200'
    body = json.loads(result['body'])
    url = list(body.keys())[0]
    assert '42' in url
    assert 'Hitchhikers' in url
    print(result)

