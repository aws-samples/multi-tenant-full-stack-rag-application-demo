#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pytest
import boto3
import json
# from moto import mock_aws
import os
from multi_tenant_full_stack_rag_application.bedrock_provider import BedrockProvider
from multi_tenant_full_stack_rag_application import utils 

emb_model_id = "amazon.titan-embed-text-v2:0"

@pytest.fixture()
def bedrock_clients():
    # with mock_aws():
    return {
        "bedrock_client": boto3.client('bedrock'),
        "bedrock_agent_client": boto3.client('bedrock-agent'),
        "bedrock_agent_rt_client": boto3.client('bedrock-agent-runtime'),
        "bedrock_rt_client": boto3.client('bedrock-runtime'),
    }

@pytest.fixture()
def bedrock_provider(bedrock_clients):
    ssm_client = utils.BotoClientProvider.get_client('ssm')
    #with mock_aws():
    args = {
        **bedrock_clients,
        "ssm_client": ssm_client,
    }
    yield BedrockProvider(**args)


def test_create_bedrock_provider(bedrock_provider):
    assert isinstance(bedrock_provider, BedrockProvider)

def test_get_list_models(
    bedrock_provider,
    monkeypatch
):  
    pass

def test_get_model_dimensions(bedrock_provider):
    # with mock_aws():
    assert bedrock_provider.get_model_dimensions(
        emb_model_id
    ) == 1024

def test_get_max_model_tokens(bedrock_provider):
    #  with mock_aws():
    assert bedrock_provider.get_model_max_tokens(
        emb_model_id
    ) == 8192

def test_get_model_max_tokens():
    pass

def test_post_embed_text(bedrock_provider): # , monkeypatch):
    # # print(f"test_post_embed_text received ssm client with params {ssm_client.describe_parameters(MaxResults=50)}")
    # # print(f"Got identity_pool_id {identity_pool_id}")
    identity_pool_id = os.getenv('IDENTITY_POOL_ID')
    ssm_client = utils.BotoClientProvider.get_client('ssm')
    origin = 'mtfsradbdevEmbeddingsProv-EmbeddingsProviderFuncti-n8zrGz2jNKOB'
    
    #with mock_aws(): 
    user_id = os.getenv('CG_UID')
    expected_model_id = emb_model_id
    event = {
        "operation": "embed_text",
        "origin": origin,
        "args": {
            "model_id": emb_model_id,
            "input_text": "This is a dog",
            "dimensions": 1024,
            "input_type": "search_query"
        }
    }

    with open('multi_tenant_full_stack_rag_application/bedrock_provider/embed_text_titan_v2_1024.json', 'r') as f_in:
        expected_result = json.load(f_in)

    model_kwargs = {
        "dimensions": 1024
    }
    result = bedrock_provider.handler(event, {})
    print(f"Got result {result}")
    assert len(result['response']) == 1024
    # assert result['path'] == '/bedrock_provider'
    # assert result['operation'] == 'embed_text'
    # assert result['method'] == 'POST'
    assert result['statusCode'] == 200
    # # print(result.keys())

def test_post_invoke_model(bedrock_provider, monkeypatch):
    pass

def test_post_get_semantic_similarity(bedrock_provider):
    # with mock_aws():
    text1 = 'This is a dog'
    text2 = 'This is a dog'

    result = bedrock_provider.get_semantic_similarity(
        text1, 
        text2,
        emb_model_id, 
        1024
    )
    assert result == 1 or str(result)[:4] == '1.00'

    result = bedrock_provider.get_semantic_similarity(
        text1, 
        text2,
        emb_model_id, 
        512
    )
    assert result == 1 or str(result)[:4] == '1.00'

    result = bedrock_provider.get_semantic_similarity(
        text1, 
        text2,
        emb_model_id, 
        256
    )
    assert result == 1 or (str(result)[:4] in ['0.99','1.00'])

    text3 = "This is not a dog"
    result = bedrock_provider.get_semantic_similarity(
        text1, 
        text3,
        emb_model_id, 
        1024
    )
    assert str(result)[:4] == '0.56'


def test_post_get_token_count():
    pass

    