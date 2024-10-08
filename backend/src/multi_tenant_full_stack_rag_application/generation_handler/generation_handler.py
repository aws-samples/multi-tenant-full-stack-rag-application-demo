#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module
from pathlib import Path

from multi_tenant_full_stack_rag_application.auth_provider import AuthProvider, AuthProviderFactory
from multi_tenant_full_stack_rag_application.bedrock_provider import BedrockProvider
from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.document_collections_handler.document_collections_handler import DocumentCollectionsHandler
from multi_tenant_full_stack_rag_application.document_collections_handler.document_collections_handler_factory import DocumentCollectionsHandlerFactory
# from multi_tenant_full_stack_rag_application.memory_provider import ChatMessage, ChatConversation, MemoryProvider
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider_factory import EmbeddingsProviderFactory
from multi_tenant_full_stack_rag_application.enrichment_pipelines.entity_extraction import neptune_client as neptune
from multi_tenant_full_stack_rag_application.prompt_template_handler import PromptTemplate, PromptTemplateHandler
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSettingsProvider, UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_search_provider import VectorSearchProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response
from .generation_handler_event import GenerationHandlerEvent

""" 
API calls served by this function (via API Gateway):
GET /generation: list models
POST /generation: invoke model
"""

search_query_model = 'anthropic.claude-3-haiku-20240307-v1:0'

# init global variables to hold injected data, because otherwise the
# clients will be re-initialized every time the function is invoked, slowing things down.
initialized = None
emb_provider = None 
document_collections_handler = None
user_settings_provider = None 
auth_provider = None 
vsearch_provider = None
bedrock_provider = None
neptune_endpoint = None
prompt_template_handler = None
ssm = None
generation_handler = None

class GenerationHandler:
    def __init__(self, 
        auth_provider: AuthProvider,
        bedrock_provider: BedrockProvider, 
        doc_collections_handler: DocumentCollectionsHandler,
        prompt_template_handler: PromptTemplateHandler,
        ssm_client: boto3.client,
        vector_search_provider: VectorSearchProvider
    ):
        self.auth_provider = auth_provider
        self.bedrock = bedrock_provider
        self.document_collections_handler = doc_collections_handler
        self.prompt_template_handler = prompt_template_handler

        self.vector_search_provider = vector_search_provider
        origin_domain_name = ssm_client.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']

        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173' # for local development
        ]
        with open(f"{self.prompt_template_handler.prompt_template_path}/system_get_search_query.txt", 'r') as f_in:
            self.search_query_template = f_in.read()
            
        self.llms = []


    def get_conversation(self, msg_obj): 
        curr_prompt = msg_obj['human_message']
        hist = ''
        if 'memory' in msg_obj and \
            'history' in msg_obj['memory']:
            hist = msg_obj['memory']['history']
        return (hist, curr_prompt)

    def get_search_query(self, handler_evt): 
        msg_obj = handler_evt.message_obj
        (hist, curr_prompt) = self.get_conversation(msg_obj)
        doc_collections = self.document_collections_handler.get_doc_collections(handler_evt.user_id, include_shared=True)
        doc_collections_dicts = []
        print(f"get_search_query got event {handler_evt}")
        for collection_id in doc_collections:
            collection = doc_collections[collection_id]
            print(f"Got collection {collection}")
            doc_collections_dicts.append({
                'id': collection_id,
                'name': collection.collection_name,
                'description': collection.description,
                'graph_schema': json.loads(collection.graph_schema) if isinstance(collection.graph_schema, str) else collection.graph_schema,
            })

        prompt =  self.search_query_template.replace('{conversation_history}', hist)\
            .replace('{current_user_prompt}', curr_prompt)\
            .replace('{available_document_collections}', json.dumps(doc_collections_dicts, indent=2))
        print(f"get_search_query sending prompt {prompt}")
        result = self.bedrock.invoke_model(search_query_model, prompt, model_kwargs={
            "max_tokens": 300,
            "temperature": 0,
            "top_k": 250,
            "top_p": 0.999,
            "stop_sequences": ["</selected_document_collections>"]
        }).replace('<selected_document_collections>', '').strip()
        print(f"Got result from search recommendation invocation: {result}")
        if result == 'NONE':
            result = None
        else:
            try:
                result = json.loads(result)
            except Exception as e:
                print(f"Error parsing search recommendation result: {e}")
                result = None
        if result and 'vector_database_search_terms' in result:
            result['vector_database_search_terms'] = result['vector_database_search_terms'].replace(collection.collection_name, '')
        if result and 'graph_database_search_terms' in result:
            result['graph_database_search_terms'] = result['graph_database_search_terms'].replace(collection.collection_name, '')
            
        print(f"Get search query returning {result}")
        return result
        
    def handler(self, event, context):
        print(f"Got event {event}")
        event = GenerationHandlerEvent().from_lambda_event(event)
        method = event.method
        path = event.path
        if event.origin not in self.frontend_origins:
            return format_response(403, {}, None)
    
        status = 200
        user_id = None

        if event.method == 'OPTIONS': 
            result = {}
        
        if hasattr(event, 'auth_token') and event.auth_token is not None:
            user_id = self.auth_provider.get_userid_from_token(event.auth_token)
            event.user_id = user_id

        if event.method == 'GET': 
            if self.llms == []:
                models = self.bedrock.list_models()
                result = {
                    "models": [],
                    "model_default_params": self.bedrock.model_params
                }
            
                for model in models:
                    result["models"].append(model['modelId'])
                result['models'].sort()
                self.llms = result
            else:
                result = self.llms

        elif event.method == 'POST':
            msg_obj = event.message_obj
            context = ''
            if 'document_collections' in msg_obj:
                # first assemble the chat history and find a sensible set of
                # search terms given the most recent question
                msg_obj['user_id'] = user_id
                search_recommendations = self.get_search_query(event)   
                print(f"Got search_recommendations: {search_recommendations}")
                if search_recommendations is not None:                 
                    # do the context search in the given doc collections.
                    if "vector_database_search_terms" in search_recommendations and \
                        search_recommendations['vector_database_search_terms'] != '':
                        rag_results = self.vector_search_provider.semantic_search(
                            search_recommendations
                        )
                        context += "<vector_context>\n"
                        for doc in rag_results:
                            if isinstance(doc, str):
                                doc = json.loads(doc.strip())
                            context += doc['content']
                        context += "</vector_context>\n\n"
                    if "graph_database_query" in search_recommendations and \
                        search_recommendations['graph_database_query'] != '':
                        graph_query = search_recommendations['graph_database_query']
                        context += f"<graph_context>\n<graph_query>\n{graph_query}\n</graph_query>\n"
                        context += "<graph_query_results>\n"
                        print(f"Running neptune query {graph_query}")
                        neptune_response = neptune.make_signed_request(neptune_endpoint, 'POST', 'openCypher', graph_query)
                        if isinstance(neptune_response, str):
                            neptune_response = json.loads(neptune_response)
                        print(f"Got neptune response {neptune_response}")
                        results = neptune_response['results']
                        final_results = []
                        for obj in results:
                            val = list(obj.values())[0]
                            if val not in final_results:
                                print(f"adding val {val} to final_results")
                                final_results.append(val)
                        # {'results': [{'node_types': ['person']}, {'node_types': ['document']}, {'node_types': ['contingency']}, {'node_types': ['company']}, {'node_types': ['property']}]}
                        context += "\n".join(final_results) + "\n</graph_query_results>\n</graph_context>\n\n"
                    
            (hist, curr_prompt) = self.get_conversation(msg_obj)
            print(f'msg_obj before get_prompt_template {msg_obj}')
            print(f"Getting prompt {msg_obj['prompt_template']}")
            template = self.prompt_template_handler.get_prompt_template(user_id, msg_obj['prompt_template'])
            print(f"Got prompt template: {template}")
            prompt = template.template_text.replace('{context}', context).replace('{user_prompt}', curr_prompt).replace('{conversation_history}', hist)
            model_args = msg_obj['model']['model_args']
            print(f"sending model_args {model_args}")
            print(f"sending populated prompt {prompt}")
            result = self.bedrock.invoke_model(msg_obj['model']['model_id'], prompt, model_args)
        
        return format_response(status, result, event.origin)


def handler(event, context):
    global initialized, emb_provider, document_collections_handler, neptune_endpoint, user_settings_provider, auth_provider, \
        vsearch_provider, bedrock_provider, ssm, prompt_template_handler, generation_handler
    if not initialized:
        emb_provider = EmbeddingsProviderFactory.get_embeddings_provider()
        user_settings_provider = UserSettingsProviderFactory.get_user_settings_provider()
        auth_provider = AuthProviderFactory.get_auth_provider()
        document_collections_handler = DocumentCollectionsHandlerFactory.get_document_collections_handler()
        vsearch_provider = VectorSearchProvider(
            document_collections_handler,
            user_settings_provider,
            VectorStoreProviderFactory.get_vector_store_provider()
        )
        bedrock_provider = BedrockProvider()
        ssm =BotoClientProvider.get_client('ssm')
        prompt_template_handler=PromptTemplateHandler(
                auth_provider,
                ssm,
                user_settings_provider
        )
        neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT')
        generation_handler = GenerationHandler(
            auth_provider,
            bedrock_provider,
            document_collections_handler,
            prompt_template_handler,
            ssm,
            vsearch_provider
        )
        initialized = True

    return generation_handler.handler(event, context)


if __name__=='__main__':
    print("Running GenerationHandler as main")
    with open ('multi_tenant_full_stack_rag_application/generation_handler/example_incoming_event2.json', 'r') as f_in:
        event =json.loads(f_in.read())
    handler(event, None)