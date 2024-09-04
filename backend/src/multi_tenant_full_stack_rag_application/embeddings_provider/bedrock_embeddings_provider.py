#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3 
from botocore.config import Config
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider, EmbeddingsProviderEvent, EmbeddingType
from multi_tenant_full_stack_rag_application.utils import invoke_service

"""
API

GET /embeddings_provider/{operation}/{model_id}...
        {get_model_dimensions}/{model_id}: fetch list of dimensions for a given model
        {get_model_max_tokens}/{model_id}: fetch max tokens for a given model

POST /embeddings_provider/{operation}...
        {encode}: embed the given text and return a vector.
        post body = {
            'input_text': 'text to embed',
            'model_id': 'model_id',
            'dimensions': 1024
        }

        {get_token_count}: return the estimated number of tokens in a string
        post body = {
            "input_text": "text to count tokens for"
        }
            
"""


# create  Config object for 10 max retries in adaptive mode
config = Config(
    retries=dict(
        max_attempts=10
    )
)
split_seqs = ['\n\n\n', '\n\n', '\n', '. ', ' ']
completed_files = []

bedrock_embeddings_provider = None


class BedrockEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, 
        model_id,
        dimensions=None,
        b_client = boto3.client('bedrock', config=config),
        ba_client = boto3.client('bedrock-agent', config=config),
        bar_client = boto3.client('bedrock-agent-runtime', config=config),
        br_client = boto3.client('bedrock-runtime', config=config)
    ):
        self.model_id = model_id
        self.bedrock = BedrockProvider(
            b_client, ba_client, bar_client, br_client
        )
        self.model_max_tokens = self.get_model_max_tokens()

    def encode(self, input_text, input_type=EmbeddingType.search_query, *, dimensions=1024):
        return self.bedrock.embed_text(input_text, self.model_id)

    def get_model_dimensions(self):
        return self.bedrock.get_model_dimensions(self.model_id)

    def get_model_max_tokens(self):
        if not (hasattr(self, 'model_max_tokens') and self.model_max_tokens):
            self.model_max_tokens = self.bedrock.get_model_max_tokens(self.model_id)
        return self.model_max_tokens

    def get_token_count(self, input_text): 
        return self.bedrock.get_token_count(input_text)

    def handler(self, event, context):
        handler_evt = EmbeddingsProviderEvent.from_lambda_event(event)

        if handler_evt == 'GET':
    
def handler(event, context):
    global bedrock_embeddings_provider
    if not bedrock_embeddings_provider:
        model_id = event['model_id']
        dimensions = 1024 if not 'dimensions' \
            in event \
            else event['dimensions']
        
        bedrock_embeddings_provider = BedrockEmbeddingsProvider(
            model_id, dimensions
        )

    

