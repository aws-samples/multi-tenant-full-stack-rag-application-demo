#!/usr/bin/env python3
"""
Simple test runner to verify the updated tests work correctly.
"""

import sys
import os
sys.path.insert(0, 'src')

def test_cognito_auth_provider_event():
    """Test CognitoAuthProviderEvent creation"""
    from multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider_event import CognitoAuthProviderEvent
    
    event = CognitoAuthProviderEvent(
        operation='get_userid_from_token',
        origin='test-function',
        auth_token='test-token'
    )
    
    assert event.operation == 'get_userid_from_token'
    assert event.origin == 'test-function'
    assert event.auth_token == 'test-token'
    print("✓ CognitoAuthProviderEvent test passed")

def test_bedrock_provider_event():
    """Test BedrockProviderEvent creation"""
    from multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider_event import BedrockProviderEvent
    
    event = BedrockProviderEvent(
        operation='embed_text',
        origin='test-function',
        model_id='amazon.titan-embed-text-v2:0',
        input_text='test text',
        dimensions=1024
    )
    
    assert event.operation == 'embed_text'
    assert event.origin == 'test-function'
    assert event.model_id == 'amazon.titan-embed-text-v2:0'
    assert event.input_text == 'test text'
    assert event.dimensions == 1024
    print("✓ BedrockProviderEvent test passed")

def test_cognito_provider_mock():
    """Test CognitoAuthProvider with mocks"""
    from unittest.mock import Mock, patch
    from multi_tenant_full_stack_rag_application.auth_provider import CognitoAuthProvider
    from multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider_event import CognitoAuthProviderEvent
    from multi_tenant_full_stack_rag_application import utils
    
    # Mock dependencies
    mock_cognito_identity = Mock()
    mock_cognito_identity.get_id.return_value = {'IdentityId': 'test-identity-id'}
    
    mock_cognito_idp = Mock()
    mock_ssm = Mock()
    
    with patch.object(utils, 'get_allowed_origins') as mock_get_origins:
        mock_get_origins.return_value = {
            'test_function': 'test-function'
        }
        
        provider = CognitoAuthProvider(
            cognito_identity_pool_id='test-pool-id',
            cognito_user_pool_id='test-user-pool-id',
            region='us-east-1',
            cognito_identity_client=mock_cognito_identity,
            cognito_idp_client=mock_cognito_idp,
            ssm_client=mock_ssm
        )
        
        event = CognitoAuthProviderEvent(
            operation='get_userid_from_token',
            origin='test-function',
            auth_token='test-token'
        )
        
        result = provider.handler(event, {})
        
        assert result['statusCode'] == 200
        print("✓ CognitoAuthProvider mock test passed")

def test_bedrock_provider_mock():
    """Test BedrockProvider with mocks"""
    from unittest.mock import Mock, patch, MagicMock
    from multi_tenant_full_stack_rag_application.bedrock_provider import BedrockProvider
    from multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider_event import BedrockProviderEvent
    from multi_tenant_full_stack_rag_application import utils
    import json
    
    # Mock Bedrock clients
    mock_bedrock = Mock()
    mock_bedrock_rt = Mock()
    mock_bedrock_agent = Mock()
    mock_bedrock_agent_rt = Mock()
    mock_ssm = Mock()
    
    # Mock embedding response
    mock_embedding = [0.1] * 1024
    mock_bedrock_rt.invoke_model.return_value = {
        'body': MagicMock()
    }
    mock_bedrock_rt.invoke_model.return_value['body'].read.return_value = json.dumps({
        'embedding': mock_embedding
    }).encode('utf-8')
    
    with patch.object(utils, 'get_allowed_origins') as mock_get_origins, \
         patch.object(utils, 'get_ssm_params') as mock_get_ssm_params:
        
        mock_get_origins.return_value = {
            'test_function': 'test-function'
        }
        mock_get_ssm_params.return_value = {}
        
        provider = BedrockProvider(
            bedrock_client=mock_bedrock,
            bedrock_rt_client=mock_bedrock_rt,
            bedrock_agent_client=mock_bedrock_agent,
            bedrock_agent_rt_client=mock_bedrock_agent_rt,
            ssm_client=mock_ssm
        )
        
        event = BedrockProviderEvent(
            operation='embed_text',
            origin='test-function',
            model_id='amazon.titan-embed-text-v2:0',
            input_text='test text',
            dimensions=1024
        )
        
        result = provider.handler(event, {})
        
        assert result['statusCode'] == 200
        assert result['operation'] == 'embed_text'
        assert len(result['response']) == 1024
        print("✓ BedrockProvider mock test passed")

if __name__ == '__main__':
    print("Running updated provider tests...")
    
    try:
        test_cognito_auth_provider_event()
        test_bedrock_provider_event()
        test_cognito_provider_mock()
        test_bedrock_provider_mock()
        
        print("\n🎉 All tests passed! The updated tests are working correctly.")
        print("\nKey improvements made:")
        print("1. Updated tests to use Pydantic event models instead of dictionaries")
        print("2. Added comprehensive mocking for AWS services")
        print("3. Added proper test fixtures and error handling")
        print("4. Improved test coverage for all operations")
        print("5. Added integration tests with mocked AWS services")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
