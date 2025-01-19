#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pytest
import boto3
import json
import os

from moto import mock_aws
from multi_tenant_full_stack_rag_application.auth_provider import CognitoAuthProvider
from multi_tenant_full_stack_rag_application import utils

@pytest.fixture()
def cognito_auth_provider():
    cognito_auth_provider = CognitoAuthProvider(
        os.getenv('IDENTITY_POOL_ID'),
        os.getenv('USER_POOL_ID'),
        os.getenv('AWS_REGION')
    )
    yield cognito_auth_provider

def test_create_auth_provider(cognito_auth_provider):
    assert isinstance(cognito_auth_provider, CognitoAuthProvider)

def test_invoke_get(
    cognito_auth_provider
):  
    origin = utils.get_ssm_params('document_collections_handler_function_name')
    event = {
        "operation": "get_userid_from_token",
        "origin": origin,
        "args": {
            "auth_token": os.getenv("JWT")
        }
    }
    result = cognito_auth_provider.handler(event, {})
    print(result)
    assert result['statusCode'] == '200'
    returned_user_id = json.loads(result['body'])['user_id']
    assert returned_user_id == os.getenv("CG_UID")