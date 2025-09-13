#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
import json
import os
from math import ceil

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider, utils
from .embeddings_provider import EmbeddingsProvider, EmbeddingType
from .embeddings_provider_factory import EmbeddingsProviderFactory
from .embeddings_provider_event import EmbeddingsProviderEvent


sm_embeddings_provider = None


class SageMakerEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, 
        endpoint: str,
        model_id: str,
        dimensions: int,
        max_tokens: int,
        use_embedding_type: bool=True
    ):
        super().__init__()
        self.endpoint = endpoint
        self.model_id = model_id
        self.dimensions = dimensions
        self.max_tokens = max_tokens
        self.sm_client = BotoClientProvider.get_client('sagemaker-runtime')
        self.utils = utils
        self.allowed_origins = self.utils.get_allowed_origins()
        self.use_embedding_type = use_embedding_type


    def embed_text(self, input_text, embedding_type=EmbeddingType.search_query):
        if self.use_embedding_type:
            # this should be embedding_type.name to get the text of the ENUM, not embedding_type.value.
            input_text = embedding_type.name + ': ' + input_text
        response = self.sm_client.invoke_endpoint(
            EndpointName=self.endpoint,
            Body=json.dumps({"inputs": input_text}).encode('utf-8'),
            ContentType="application/json",
            Accept="*/*"
        )
        return json.loads(response['Body'].read())

    def get_model_dimensions(self, model_id=None) -> int:
        return self.dimensions
    
    def get_model_max_tokens(self, model_id=None) -> int:
        return self.max_tokens

    def get_token_count(self, input_text) -> int:
        #estimate 1.3 tokens per word on average
        return ceil(len(input_text.split()) * 1.3)
    
    def handler(self, event, context):
        print(f"SageMakerEmbeddingsProvider received event {event}")
        handler_evt = EmbeddingsProviderEvent().from_lambda_event(event)
        if not hasattr(handler_evt,'model_id') or handler_evt.model_id == '':
            handler_evt.model_id = self.model_id
            
        print(f"handler_evt is {handler_evt.__dict__}")
        status = 200
        result = {}

        if handler_evt.origin not in self.allowed_origins.values():
            print(f"{handler_evt.origin} is not in {self.allowed_origins.values()}. Returning 403")
            result = {'error': 'Access denied'}
            status = 403

        elif handler_evt.operation == 'embed_text':
            # Convert string embedding_type to EmbeddingType enum
            embedding_type = EmbeddingType.search_query  # default
            if hasattr(handler_evt, 'embedding_type') and handler_evt.embedding_type:
                if handler_evt.embedding_type == 'search_document':
                    embedding_type = EmbeddingType.search_document
                elif handler_evt.embedding_type == 'search_query':
                    embedding_type = EmbeddingType.search_query
            
            response = self.embed_text(handler_evt.input_text, embedding_type)
            print(f"Got response from self.embed_text {response}")
            result = {
                "response": response,
            }

        elif handler_evt.operation == 'get_model_dimensions':
            response = self.get_model_dimensions(handler_evt.model_id)
            result = {
                "response": response,
            }

        elif handler_evt.operation == 'get_model_max_tokens':
            max_tokens = self.get_model_max_tokens(handler_evt.model_id)
            print(f"Got response from get_model_max_tokens: {max_tokens}")
            result = {
                "response": max_tokens,
            }

        elif handler_evt.operation == 'get_token_count':
            result = {
                "response": self.get_token_count(handler_evt.input_text)
            }

        return self.utils.format_response(status, result, handler_evt.origin)
    

    
def handler(event, context):
    print(f'sm_embeddings_provider.handler got event {event}')
    global sm_embeddings_provider
    if not sm_embeddings_provider:
        sm_embeddings_provider = EmbeddingsProviderFactory.get_embeddings_provider()
    return sm_embeddings_provider.handler(event, context)
