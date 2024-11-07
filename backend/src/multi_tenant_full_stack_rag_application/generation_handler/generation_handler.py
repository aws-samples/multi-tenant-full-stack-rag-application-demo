#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module
from pathlib import Path
from multi_tenant_full_stack_rag_application import utils
from .generation_handler_event import GenerationHandlerEvent

""" 
API calls served by this function (via API Gateway):
GET /generation: list models
POST /generation: invoke model
"""

search_query_model = 'anthropic.claude-3-haiku-20240307-v1:0'
default_top_k = 5

# init global variables to hold injected data, because otherwise the
# clients will be re-initialized every time the function is invoked, slowing things down.
generation_handler = None

class GenerationHandler:
    def __init__(self,
        search_template_path=None
    ):
        if not search_template_path:
            search_template_path = "multi_tenant_full_stack_rag_application/generation_handler/system_get_search_query.txt"
        self.utils = utils
        self.my_origin = self.utils.get_ssm_params('origin_generation_handler')
        
        with open(search_template_path, 'r') as f_in:
            self.search_query_template = f_in.read()
            
        self.llms = None
        self.top_k = os.getenv('TOP_K', default_top_k)

    def get_conversation(self, msg_obj): 
        curr_prompt = msg_obj['human_message']
        hist = ''
        if 'memory' in msg_obj and \
            'history' in msg_obj['memory']:
            hist = msg_obj['memory']['history']
        return (hist, curr_prompt)

    def get_search_query(self, handler_evt): 
        print(f"get_search_query got handler_evt {handler_evt.__dict__()}")
        msg_obj = handler_evt.message_obj
        (hist, curr_prompt) = self.get_conversation(msg_obj)
        doc_collections = self.utils.get_document_collections(handler_evt.user_id, origin=self.my_origin)
        print(f"get_search_query got doc_collections {doc_collections}")
        doc_collections_dicts = []
        collection_names = list(doc_collections.keys())
        for collection_name in collection_names:
            if len(msg_obj['document_collections']) > 0 and \
                not collection_name in msg_obj['document_collections']:
                continue
            print(f"get_search_query processing collection {collection_name}")
            collection = doc_collections[collection_name]
            doc_collections_dicts.append({
                'id': collection['collection_id'],
                'name': collection['collection_name'],
                'description': collection['description'],
                'graph_schema': json.loads(collection['graph_schema']) if isinstance(collection['graph_schema'], str) else collection['graph_schema'],
            })

        prompt =  self.search_query_template.replace('{conversation_history}', hist)\
            .replace('{current_user_prompt}', curr_prompt)\
            .replace('{available_document_collections}', json.dumps(doc_collections_dicts, indent=2))
        
        print(f"get_search_query sending prompt {prompt}")
        
        response = self.utils.invoke_bedrock(
            "invoke_model",
            {
                "model_id": search_query_model,
                "prompt": prompt,
                "model_kwargs": {
                    "max_tokens": 300,
                    "temperature": 0,
                    "top_k": 250,
                    "top_p": 0.999,
                    "stop_sequences": ["</selected_document_collections>"]
                }
            },
            self.my_origin
        )
        print(f"Got response from bedrock: {response}")
        status = response['statusCode']
        if not status == 200:
            print(f"Error invoking bedrock: {response}")
            return None
        response = response['response']
        response = response.replace('<selected_document_collections>', '').strip()
        print(f"generation_handler.get_search_query got response {response}")
        # print(f"Got result from search recommendation invocation: {result}")
        result = {}
        if response == 'NONE':
            response = None
        else:
            try:
                response = json.loads(response)
            except Exception as e:
                print(f"Error parsing search recommendation response: {e}")
                response = None
        if response:
            for search_rec in response:
                collection_id = search_rec['id']
                if not collection_id in result:
                    result[collection_id] = {}
                if 'vector_database_search_terms' in search_rec:
                    result[collection_id]['vector_database_search_terms'] = search_rec['vector_database_search_terms'].replace(collection['collection_name'], '')
                if 'graph_database_search_terms' in search_rec:
                    result[collection_id]['graph_database_search_terms'] = search_rec['graph_database_search_terms'].replace(collection['collection_name'], '')
                
        print(f"Get search query returning {result}")
        return result
        
    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = GenerationHandlerEvent().from_lambda_event(event)
        print(f"Got generationHandlerEvent {handler_evt.__dict__()}, type {type(handler_evt)}")
        method = handler_evt.method
        path = handler_evt.path

        status = 200
        user_id = None

        if handler_evt.method == 'OPTIONS': 
            result = {}
        
        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            print("Getting user ID from auth token")
            user_id = self.utils.get_userid_from_token( 
                handler_evt.auth_token,
                self.my_origin
            )
            print(f"Got user_id {user_id}")
            handler_evt.user_id = user_id
        print(f"Event is now {handler_evt.__dict__()}")

        if handler_evt.method == 'GET': 
            pass
            # if self.llms == []:
            #     # TODO replace with call to utils.invoke_service
            #     # models = self.bedrock.list_models()
            #     result = {
            #         "models": [],
            #         "model_default_params": self.bedrock.model_params
            #     }
            
            #     for model in models:
            #         result["models"].append(model['modelId'])
            #     result['models'].sort()
            #     self.llms = result
            # else:
            #     result = self.llms

        elif handler_evt.method == 'POST':
            msg_obj = handler_evt.message_obj
            context = ''
            if 'document_collections' in msg_obj:
                # first assemble the chat history and find a sensible set of
                # search terms given the most recent question
                msg_obj['user_id'] = user_id
                search_recommendations = self.get_search_query(handler_evt)   
                print(f"Got search_recommendations: {search_recommendations}, type {type(search_recommendations)}")
                vector_search_recommendations = []
                graph_search_recommendations = []
                for collection_id in list(search_recommendations.keys()):
                    search_recommendation = search_recommendations[collection_id]
                    if "vector_database_search_terms" in search_recommendation and \
                        search_recommendation['vector_database_search_terms'] != '':
                        # TODO replace with call to utils.invoke_service
                        # search_terms = search_recommendations['vector_database_search_terms']
                        #  {'ea85934edaaa4270bac14b4e7c69bce9': {'vector_database_search_terms': 'buyers, released, contingencies'}}                        vector_search_recommendations.append({

                        vector_search_recommendations.append({
                            "id": collection_id,
                            "vector_database_search_terms": search_recommendation['vector_database_search_terms']
                        })
                        
                    if "graph_database_query" in search_recommendation and\
                        search_recommendation['graph_database_query'] != '':
                        graph_search_recommendations.append({
                            "id": collection_id,
                            "graph_database_search_terms": search_recommendation['graph_database_search_terms']
                        })

                if len(vector_search_recommendations) > 0:
                    response = self.utils.search_vector_docs(vector_search_recommendations, self.top_k, self.my_origin)
                    print(f"Got rag_results {response}")
                    rag_results = json.loads(response['body'])
                    context += "<vector_context>\n"
                    for doc in rag_results:
                        context += doc['content']
                    context += "</vector_context>\n\n"

                graph_results = []
                for recommendation in graph_search_recommendations:
                    graph_query = recommendation['graph_database_query']
                    response = self.utils.neptune_statement(collection['collection_id'], graph_query, 'openCypher', self.my_origin)
                    print(f"Got neptune respnonse {response}")
                    graph_results.append(response)
                    print(f"Got graph_results {graph_results}")
                
                if len(graph_results) > 0:
                    graph_results = "\n".join(graph_results)
                    # TODO replace with call to utils.invoke_service
                    context += f"<graph_context>\n<graph_query>\n{graph_query}\n</graph_query>\n"
                    context += f"<graph_query_results>\n{graph_results}\n</graph_query_results>\n"
                            
            (hist, curr_prompt) = self.get_conversation(msg_obj)
            print(f'msg_obj before get_prompt_template {msg_obj}')
            # TODO replace with call to utils.invoke_service
            template_response = self.utils.get_prompt_template(msg_obj['prompt_template'], user_id, self.my_origin)
            # template = self.prompt_template_handler.get_prompt_template(user_id, msg_obj['prompt_template'])
            # template = get_prompt_template(template_id, user_id, self.my_origin)
            print(f"Got prompt template response: {template_response}")
            body = json.loads(template_response['body'])
            template = body[msg_obj['prompt_template']]
            prompt = template['template_text'].replace('{context}', context).replace('{user_prompt}', curr_prompt).replace('{conversation_history}', hist)
            model_args = msg_obj['model']['model_args']
            print(f"sending model_args {model_args}")
            print(f"sending populated prompt {prompt}")
            # TODO replace with call to utils.invoke_service
            print()
            result = self.utils.invoke_bedrock(
                'invoke_model', 
                {
                    "model_id": msg_obj['model']['model_id'], 
                    "prompt": prompt, 
                    "model_kwargs": model_args
                },
                self.my_origin
            )
            print(f"Got result from bedrock: {result}")
            if not result["statusCode"] == 200:
                raise Exception(f"Failed to invoke bedrock {result}")
            else:
                result = result['response']
        return utils.format_response(status, result, handler_evt.origin)


def handler(event, context):
    global generation_handler
    if not generation_handler:
        generation_handler = GenerationHandler()
    return generation_handler.handler(event, context)


if __name__=='__main__':
    # print("Running GenerationHandler as main")
    with open ('multi_tenant_full_stack_rag_application/generation_handler/example_incoming_event2.json', 'r') as f_in:
        event =json.loads(f_in.read())
    handler(event, None)