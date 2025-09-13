#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pytest
import boto3
import json
import os
from unittest.mock import Mock, patch

from moto import mock_aws
from multi_tenant_full_stack_rag_application.auth_provider import CognitoAuthProvider
from multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider_event import CognitoAuthProviderEvent
from multi_tenant_full_stack_rag_application import utils

@pytest.fixture()
def mock_ssm_client():
    """Mock SSM client for testing"""
    mock_client = Mock()
    mock_client.get_parameters.return_value = {
        'Parameters': [
            {'Name': 'origin_frontend', 'Value': 'http://localhost:5173'},
            {'Name': 'document_collections_handler_function_name', 'Value': 'test-function'}
        ]
    }
    return mock_client

@pytest.fixture()
def mock_cognito_identity_client():
    """Mock Cognito Identity client for testing"""
    mock_client = Mock()
    mock_client.get_id.return_value = {
        'IdentityId': 'test-identity-id-12345'
    }
    return mock_client

@pytest.fixture()
def mock_cognito_idp_client():
    """Mock Cognito IDP client for testing"""
    mock_client = Mock()
    return mock_client

@pytest.fixture()
def cognito_auth_provider(mock_ssm_client, mock_cognito_identity_client, mock_cognito_idp_client):
    """Create CognitoAuthProvider with mocked dependencies"""
    with patch.object(utils, 'get_allowed_origins') as mock_get_origins:
        mock_get_origins.return_value = {
            'origin_frontend': 'http://localhost:5173',
            'document_collections_handler_function_name': 'test-function'
        }
        
        provider = CognitoAuthProvider(
            cognito_identity_pool_id='test-identity-pool-id',
            cognito_user_pool_id='test-user-pool-id',
            region='us-east-1',
            cognito_identity_client=mock_cognito_identity_client,
            cognito_idp_client=mock_cognito_idp_client,
            ssm_client=mock_ssm_client
        )
        yield provider

def test_create_auth_provider(cognito_auth_provider):
    """Test that CognitoAuthProvider can be instantiated"""
    assert isinstance(cognito_auth_provider, CognitoAuthProvider)
    assert cognito_auth_provider.identity_pool_id == 'test-identity-pool-id'
    assert cognito_auth_provider.user_pool_id == 'test-user-pool-id'

def test_get_userid_from_token(cognito_auth_provider):
    """Test getting user ID from auth token"""
    test_token = "test-jwt-token"
    user_id = cognito_auth_provider.get_userid_from_token(test_token)
    
    assert user_id == 'test-identity-id-12345'
    cognito_auth_provider.cognito_identity.get_id.assert_called_once()

def test_handler_get_userid_from_token_success(cognito_auth_provider):
    """Test successful get_userid_from_token operation"""
    event = CognitoAuthProviderEvent(
        operation="get_userid_from_token",
        origin="test-function",
        args={
            "auth_token": "test-jwt-token",
        }
    )
    
    result = cognito_auth_provider.handler(event, {})
    
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert response_body['user_id'] == 'test-identity-id-12345'

def test_handler_forbidden_origin(cognito_auth_provider):
    """Test handler with forbidden origin"""
    event = CognitoAuthProviderEvent(
        operation="get_userid_from_token",
        origin="unauthorized-origin",
        args={
            "auth_token": "test-jwt-token",
        }   
    )
    
    result = cognito_auth_provider.handler(event, {})
    
    assert result['statusCode'] == 403
    assert json.loads(result['body']) == 'forbidden'

def test_handler_invalid_operation(cognito_auth_provider):
    """Test handler with invalid operation"""
    event = CognitoAuthProviderEvent(
        operation="invalid_operation",
        origin="test-function",
        args={
            "auth_token": "test-jwt-token",
        }   
    )
    
    result = cognito_auth_provider.handler(event, {})
    
    assert result['statusCode'] == 400
    response_body = json.loads(result['body'])
    assert "ERROR: Unexpected method or path sent" in response_body

def test_handler_empty_auth_token(cognito_auth_provider):
    """Test handler with empty auth token"""
    event = CognitoAuthProviderEvent(
        operation="get_userid_from_token",
        origin="test-function",
        args={
            "auth_token": "",
        }   
    )
    
    result = cognito_auth_provider.handler(event, {})
    
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert response_body['user_id'] == ''

@mock_aws
def test_integration_with_real_aws_services():
    """Integration test with mocked AWS services"""
    # This test uses moto to mock AWS services
    with patch.object(utils, 'get_allowed_origins') as mock_get_origins:
        mock_get_origins.return_value = {
            'origin_frontend': 'http://localhost:5173',
            'test_function': 'test-function'
        }
        
        provider = CognitoAuthProvider(
            cognito_identity_pool_id='us-east-1:test-pool-id',
            cognito_user_pool_id='us-east-1_TestPool',
            region='us-east-1'
        )
        
        # Test that the provider was created successfully
        assert isinstance(provider, CognitoAuthProvider)
        assert provider.identity_pool_id == 'us-east-1:test-pool-id'
        assert provider.user_pool_id == 'us-east-1_TestPool'
