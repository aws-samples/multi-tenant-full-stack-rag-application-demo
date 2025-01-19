import pytest
import boto3
import json
import os
import sys
from zipfile import ZipFile

sys.path.insert(0, '../src')
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox_tool.code_sandbox_tool import CodeSandboxTool
from multi_tenant_full_stack_rag_application import utils

s3 = boto3.client('s3')

@pytest.fixture(scope="session")
def code_sandbox_tool():
    return CodeSandboxTool()

def test_create_code_sandbox_tool(code_sandbox_tool):
    assert isinstance(code_sandbox_tool, CodeSandboxTool)

    # code_sandbox_tool
    # assert result['statusCode'] == '200'
    # body = result['body']
    # assert len(body.keys()) == 5
