#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest
from datetime import datetime
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider
from multi_tenant_full_stack_rag_application.embeddings_provider.bedrock_embeddings_provider import BedrockEmbeddingsProvider


region = os.getenv('AWS_REGION')
model_name = 'amazon.titan-embed-text-v2:0'
max_model_len = 8192

def test_bedrock_embeddings_provider():
    br = boto3.client('bedrock-runtime', region_name=region)
    bep = BedrockEmbeddingsProvider(
        model_name
    )
    
    # assert isinstance(emb, Embeddings)
    response =  bep.get_model_max_tokens(model_name)['response']
    print(f"bep.get_model_max_tokens returned {response}")
    assert response == max_model_len
    assert bep.get_token_count('This is a dog') == 6
    