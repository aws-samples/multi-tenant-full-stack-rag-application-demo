#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import json
import pytest
from datetime import datetime
from multi_tenant_full_stack_rag_application.generation_handler import GenerationHandler, GenerationHandlerEvent


region = os.getenv('AWS_REGION')

@pytest.fixture
def gh():
    gh = GenerationHandler(
        "../src/multi_tenant_full_stack_rag_application/generation_handler/system_get_orchestration.txt"
    )
    return gh

def test_create_generation_handler(gh):
    assert isinstance(gh, GenerationHandler)

def test_get_search_query(gh):
    uid = os.getenv('CG_UID')
    evt = GenerationHandlerEvent().from_lambda_event({
        "routeKey": "POST /generation",
        "requestContext": {
            "accountId": os.getenv('TEST_ACCOUNT'),
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "davetbo@amazon.com"
                    }
                }
            }
        },
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": os.getenv('ORIGIN_GENERATION_HANDLER')
        },
        "body": json.dumps({
            "messageObj": {
                "human_message": "Who were the buyers in the real estate documents collection who released contingencies?",
                "memory": {
                    "history": [
                        {
                            "ai_message": "How can I help you today?"
                        }
                    ]
                },
                "document_collections": [
                    "real_estate_documents"
                ]
            },
            "user_id": os.getenv('CG_UID')
        })
    })
    print(f"test_generation_handler sending event {evt}")
    result = gh.get_search_query(evt)
    assert result == "Who were the buyers in the real estate documents collection who released contingencies?"


def test_get_tool_list(gh):
   response = gh.get_tool_list()
   print(f"response from get_tool_list: {response}")


def test_prompt_invocation(gh):
    pass

   
    