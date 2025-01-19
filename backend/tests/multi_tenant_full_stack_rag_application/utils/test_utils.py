#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest
from datetime import datetime
from multi_tenant_full_stack_rag_application import utils


def test_format_response():
    expected = {
        'statusCode': '200', 
        'headers': {
            'Access-Control-Allow-Headers': 'Authorization, Content-Type, x-csrf-token, X-Api-Key, *', 
            'Access-Control-Allow-Credentials': 'true', 
            'Access-Control-Allow-Origin': 'http://localhost:5173', 
            'Access-Control-Allow-Methods': 'DELETE,OPTIONS,GET,POST,PUT', 
        'Vary': 'Origin'}, 
        'body': '{"result": "Success"}'
    }
    result = utils.format_response(200, {"result": "Success"}, "http://localhost:5173")
    # print(f"format_response result:\n{result}\n")
    assert result == expected

def test_get_ssm_params():
    result = utils.get_ssm_params('bedrock_provider_function_name')
    # print(f"Got bedrock_provider_function_name: {result}")

def test_invoke_bedrock():
    response = utils.invoke_bedrock(
        'invoke_model',
        {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "prompt": "What's your name?"
        },
        utils.get_ssm_params('embeddings_provider_function_name')
    )
    # print(f"test_invoke_bedrock got response {response}")

def test_invoke_lambda():
    response = utils.invoke_lambda(
        utils.get_ssm_params('bedrock_provider_function_name'),
        {
            "operation": "invoke_model",
            "origin": utils.get_ssm_params('ingestion_provider_function_name'),
            "args": {
                "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
                "prompt": "What's your name?"
            }
        }
    )
    # print(f"test_invoke_lambda got response {response}")
    assert int(response["statusCode"]) == 200

    
    