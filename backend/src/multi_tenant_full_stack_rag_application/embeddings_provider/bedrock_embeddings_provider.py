#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3 
import os
from botocore.config import Config
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider, EmbeddingType
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider_event import EmbeddingsProviderEvent
from multi_tenant_full_stack_rag_application import utils

"""
API
 event = {
    "operation": [get_model_dimensions | get_model_max_tokens | embed_text | get_token_count ]
    "origin": set to the name of the calling lambda function.
    "args" { # Dependent on operation. See below }
 }
 OPERATION:                 KWARGS
 get_model_dimensions:      model_id
 get_model_max_tokens:      model_id
 embed_text                 input_text, model_id, dimensions
 get_token_count:           input_text
"""

split_seqs = ['\n\n\n', '\n\n', '\n', '. ', ' ']
completed_files = []

bedrock_embeddings_provider = None


class BedrockEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, 
        model_id,
        dimensions=None,
        br_client=None,
        lambda_client=None,
    ):
        self.utils = utils
        self.model_id = model_id
        
        if not br_client:
            self.bedrock_rt = self.utils.BotoClientProvider.get_client('bedrock-runtime')
        else: 
            self.bedrock_rt = br_client

        if not lambda_client:
            self.lambda_ = self.utils.BotoClientProvider.get_client('lambda')
        else:
            self.lambda_ = lambda_client

        self.allowed_origins = self.utils.get_allowed_origins()
        self.my_origin = self.utils.get_ssm_params('origin_embeddings_provider')

    # @param model_id
    # @param dimensions only matters for Titan embeddings v2, where it can be 1024, 512, or 256
    # @param input_type: either "search_query" or "search_document", 
    #                    only used for Cohere embeddings.
    def embed_text(self, text, model_id=None, dimensions=1024, input_type='search_query'):
        if model_id == None:
            model_id = self.model_id
        response = self.utils.invoke_bedrock(
            "embed_text",
            {
                "dimensions": dimensions,
                "input_text": text,
                "model_id": model_id,
                "input_type": input_type
            },
            self.utils.get_ssm_params('embeddings_provider_function_name')
        )
        # print(f"Got response from embed_text: {response}")
        return response

    def get_model_dimensions(self, model_id=None):
        if model_id == None:
            model_id = self.model_id
        response = self.utils.invoke_bedrock(
            "get_model_dimensions",
            {
                "model_id": model_id
            },
            self.utils.get_ssm_params('embeddings_provider_function_name')
        )
        # print(f"Got response from get_model_dimensions: {response}")
        return response

    def get_model_max_tokens(self, model_id=None):
        if model_id == None:
            model_id = self.model_id
        response = self.utils.invoke_bedrock(
            "get_model_max_tokens",
            {
                "model_id": model_id
            },
            self.utils.get_ssm_params('embeddings_provider_function_name')
        )
        # print(f"Got response from get_model_max_tokens: {response}")
        return response

    def get_token_count(self, input_text):
        return self.utils.get_token_count(input_text)
            
    def handler(self, event, context):
        print(f"Embeddings provider received event {event}")
        handler_evt = EmbeddingsProviderEvent().from_lambda_event(event)
        if not hasattr(handler_evt,'model_id') or handler_evt.model_id == '':
            handler_evt.model_id = self.model_id
            
        # print(f"handler_evt is {handler_evt.__dict__}")
        status = 200
        result = {}

        if handler_evt.origin not in self.allowed_origins.values():
            print(f"{handler_evt.origin} is not in {self.allowed_origins.values()}. Returning 403")
            result = {'error': 'Access denied'}
            status = 403

        elif handler_evt.operation == 'embed_text':
            response = self.embed_text(handler_evt.input_text, handler_evt.model_id, handler_evt.dimensions)
            print(f"Got response from self.embed_text {response}")
            result = {
                "response": response['response'],
            }

        elif handler_evt.operation == 'get_model_dimensions':
            response = self.get_model_dimensions(handler_evt.model_id)
            result = {
                "response": response['response'],
            }

        elif handler_evt.operation == 'get_model_max_tokens':
            response = self.get_model_max_tokens(handler_evt.model_id)
            print(f"Got response from get_model_max_tokens: {response}")
            result = {
                "response": response['response'],
            }

        elif handler_evt.operation == 'get_token_count':
            result = {
                "response": self.get_token_count(handler_evt.input_text)
            }

        return self.utils.format_response(status, result, handler_evt.origin)
    
def handler(event, context):
    global bedrock_embeddings_provider
    if not bedrock_embeddings_provider:
        print(f'bedrock_embeddings_provider.handler got event {event}')
        if 'model_id' not in event['args'] or event['args']['model_id'] == '':
            model_id = os.getenv('EMBEDDINGS_MODEL_ID')
        else:
            model_id = event['args']['model_id']

        dimensions = 1024 if not 'dimensions' \
            in event['args'] \
            else event['args']['dimensions']
        bedrock_embeddings_provider = BedrockEmbeddingsProvider(
            model_id, dimensions
        )
    return bedrock_embeddings_provider.handler(event, context)

    

