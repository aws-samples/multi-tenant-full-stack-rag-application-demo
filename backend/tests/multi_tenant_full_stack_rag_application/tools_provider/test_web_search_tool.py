import pytest
import boto3
import json
import os
import sys
from lxml.html.clean import Cleaner
sys.path.insert(0, '../src')
from multi_tenant_full_stack_rag_application.tools_provider.tools.web_search_tool.web_search_tool import WebSearchTool
from multi_tenant_full_stack_rag_application import utils

account = os.getenv('AWS_ACCOUNT_ID')


@pytest.fixture(scope="session")
def web_search_tool():
    return WebSearchTool()

def test_create_web_search_tool(web_search_tool):
    evt = {
        "operation": "search_and_download",
        "args": {
            "search_query": "today's google news headlines",
            "top_x": 5
        }
    }
    result = web_search_tool.handler(evt)
    print(f"test_web_search_tool got result: {result}")
    assert result['statusCode'] == '200'
    body = result['body']
    assert len(body.keys()) == 5
