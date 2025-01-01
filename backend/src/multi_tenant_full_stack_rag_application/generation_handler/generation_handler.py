#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from lxml import objectify
import os
from importlib import import_module
from pathlib import Path
from multi_tenant_full_stack_rag_application import utils
from .generation_handler_event import GenerationHandlerEvent

from queue import Queue
from threading import Thread

""" 
API calls served by this function (via API Gateway):
GET /generation: list models
POST /generation: invoke model
"""

search_query_model = 'anthropic.claude-3-5-haiku-20241022-v1:0'
# search_query_model = 'us.amazon.nova-pro-v1:0'
default_top_k = 5

# init global variables to hold injected data, because otherwise the
# clients will be re-initialized every time the function is invoked, slowing things down.
generation_handler = None

class GenerationHandler:
    def __init__(self,
        search_template_path=None
    ):
        if not search_template_path:
            search_template_path = "multi_tenant_full_stack_rag_application/generation_handler/system_get_orchestration.txt"
        self.utils = utils
        self.my_origin = self.utils.get_ssm_params('origin_generation_handler')
        self.ingestion_bucket = self.utils.get_ssm_params('ingestion_bucket_name')
        self.tools_provider_fn = self.utils.get_ssm_params('tools_provider_function_name')

        with open(search_template_path, 'r') as f_in:
            self.search_query_template = f_in.read()
            
        self.llms = None
        self.top_k = os.getenv('TOP_K', default_top_k)
        self.tool_list = self.get_tool_list()
        self.context_queue = Queue()

    def get_context(self, 
        graph_recommendations,
        search_recommendations,
        tool_recommendations
    ):
        graph_ctx = Thread(
            target=self.get_graph_context,
            args=(self.context_queue, graph_recommendations),
            daemon=True
        )
        graph_ctx.start()

        search_ctx = Thread(
            target=self.get_semantic_search_context,
            args=(self.context_queue, search_recommendations),
            daemon=True
        )
        search_ctx.start()

        tool_ctx = Thread(
            target=self.get_tool_context,
            args=(self.context_queue, tool_recommendations),
            daemon=True
        )
        tool_ctx.start()
        graph_ctx.join()
        search_ctx.join()
        tool_ctx.join()
        self.context_queue.put(None)
        context = ''
        while True:
            result = self.context_queue.get()
            print(f"Got item from queue: {result}")
            if not result:
                break
            else:
                context += result
        print(f"Got assembled context:\n\n{context}\n\n")
        return context

    def get_conversation(self, msg_obj): 
        curr_prompt = msg_obj['human_message']
        hist = ''
        if 'memory' in msg_obj and \
            'history' in msg_obj['memory']:
            hist = msg_obj['memory']['history']
        return (hist, curr_prompt)

    def get_graph_context(self, queue, search_recommendations):
        context = "<graph_context>\n"
        try: 
            graph_results = []
            for recommendation in search_recommendations:
                graph_query = recommendation['graph_database_query'].replace('g.V()', f'g.V().has(id, startingWith("{recommendation["id"]}")')
                response = self.utils.neptune_statement(recommendation["id"], graph_query, 'gremlin', self.my_origin)
                body = json.loads(response['body'])
                print(f"Got neptune response {body}")
                graph_results.append(str(body['response']))
            print(f"Got graph_results {graph_results}")
            
            if len(graph_results) > 0:
                graph_results = "\n".join(graph_results)
                context += f"<graph_query>\n{graph_query}\n</graph_query>\n"
                context += f"<graph_query_results>\n{graph_results}\n</graph_query_results>\n"
        except Exception as e:
            print(f"ERROR: Failed to fetch graph data context.")
        context += '</graph_context>\n'
        print(f"queuing graph context result {context}")
        queue.put(context)
        return

    def get_orchestration(self, handler_evt): 
        print(f"get_orchestration got handler_evt {handler_evt.__dict__()}")
        msg_obj = handler_evt.message_obj
        print(f"Got msg_obj {msg_obj}")
        (hist, curr_prompt) = self.get_conversation(msg_obj)
        print(f"Got history {hist}, curr_prompt {curr_prompt}")
        doc_collections = self.utils.get_document_collections(handler_evt.user_id, origin=self.my_origin)
        print(f"get_orchestration got doc_collections {doc_collections}")
        doc_collections_dicts = []
        collection_names = list(doc_collections.keys())
        print(f"Got collection_names {collection_names}")
        
        if isinstance(msg_obj['document_collections'], str):
            msg_obj['document_collections'] = json.loads(msg_obj['document_collections'])

        if msg_obj['document_collections'] == ['']:
            msg_obj['document_collections'] = []

        for collection_name in collection_names:
            print(f"msg_obj['document_collections'] = {msg_obj['document_collections']}, type {type(msg_obj['document_collections'])}, len {len(msg_obj['document_collections'])}")
            if not isinstance(msg_obj['document_collections'], list):
                if collection_name not in enabled_collections:
                    print(f"skipping collection {collection_name} because it's not in {msg_obj['document_collections']}")
                    continue

            print(f"get_orchestration processing collection {collection_name}")
            collection = doc_collections[collection_name]
            print(f"collection is now {collection}")
            doc_collections_dicts.append({
                'id': collection['collection_id'],
                'name': collection['collection_name'],
                'description': collection['description'],
                'graph_schema': json.loads(collection['graph_schema']) if isinstance(collection['graph_schema'], str) else collection['graph_schema'],
            })

        print(f"doc_collections_dicts = {doc_collections_dicts}")
        prompt =  self.search_query_template.replace('{conversation_history}', hist)\
            .replace('{current_user_prompt}', curr_prompt)\
            .replace('{available_document_collections}', json.dumps(doc_collections_dicts, indent=2))\
            .replace('{available_tools}', json.dumps(self.tool_list, indent=2))
        
        print(f"get_orchestration sending prompt {prompt}")
        
        response = self.utils.invoke_bedrock(
            "invoke_model",
            {
                "modelId": search_query_model,
                "messages": [{
                    "role": "user",
                    "content": [{
                        "text": prompt
                    }]
                }],
                "inferenceConfig": {
                    "maxTokens": 1000,
                    "temperature": 0,
                    "topP": 0.999,
                    "stopSequences": ["</SELECTIONS>"]
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
        print(f"generation_handler.get_orchestration got response {response}")
        if '<final_answer>' in response and \
            '</final_answer>' not in response:
            response += '</final_answer>'
        if not '</SELECTIONS>' in response:
            # it shouldn't be there because it's the stop seq, but the xml
            # parser will complain if the initial <SELECTIONS> tag remains unclosed.
            response += '</SELECTIONS>'
        root = objectify.fromstring(response)
        result = {}

        for child in root.getchildren():
            if child == '':
                break
            else:
                if child.tag == 'final_answer':
                    result = {"final_answer": str(child.text)}
                elif child.tag == 'document_collections_selected':
                    for collection in child.getchildren():
                        coll_id = str(collection.id.text)
                        if coll_id not in result:
                            result[coll_id] = {}
                        if hasattr(collection, 'search_terms'):
                            result[coll_id]['search_terms'] = str(collection.search_terms.text)
                        if hasattr(collection, 'graph_database_query'):
                            result[coll_id]['graph_database_query'] = str(collection.graph_database_query.text)
                        if hasattr(collection, 'reasoning'):
                            result[coll_id]['reasoning'] = str(collection.reasoning.text)

                elif  child.tag == 'tools_selected':
                    for tool in child.getchildren():
                        tool_name = str(tool.id.text)
                        print(f"Tool inputs are type: {type(str(tool.tool_inputs.text))},dir: {dir(tool.tool_inputs)}, value: {str(tool.tool_inputs.text)}")
                        inputs = json.loads(str(tool.tool_inputs.text))
                        inputs["tool_name"] = tool_name
                        inputs['user_id'] = handler_evt.user_id
                        print(f"final inputs for tool: {inputs}")
                        result[tool_name] = {
                            'tool_name': tool_name,
                            'tool_inputs': inputs,
                        }

        print(f"Get_orchestration returning {result}")
        return result
        
    def get_semantic_search_context(self, queue, search_recommendations):
        context = "<semantic_search_context>\n"
        try:
            if len(search_recommendations) > 0:
                response = self.utils.search_vector_docs(search_recommendations, self.top_k, self.my_origin)
                print(f"Got rag_results {response}")
                rag_results = json.loads(response['body'])
                for doc in rag_results:
                    context += doc['content']
        except Exception as e:
            print(f"ERROR: Failed to fetch semantic search context.")
            context += 'Error: failed to fetch semantic search context.'
        context += "</semantic_search_context>\n\n"
        print(f"queuing semantic search context result {context}")
        queue.put(context)
        return

    def get_tool_context(self, queue, tool_recommendations):
        context = "<tool_context>\n"
        try:
            print(f"Tool recommendations? {tool_recommendations}")
            for recommendation in tool_recommendations:
                print(f"Got recommendation {recommendation}")
                tool_name = recommendation['tool_name']
                context += f"\t<{tool_name}_context>\n"
                if tool_name == 'file_storage_tool' and \
                'user_id' not in recommendation['tool_inputs']: 
                    recommendation['tool_inputs']['user_id'] = handler_evt.user_id
                print(f"Invoking tool {tool_name} with inputs {recommendation['tool_inputs']}")
                response = self.invoke_tool(tool_name, recommendation['tool_inputs'])  
                print(f"{recommendation['tool_name']} response {response}")   
                context += f"\n{json.dumps(response, indent=2)}\n"
                context += f"\t</{tool_name}_context>\n"
        except Exception as e:
            print(f"ERROR: Failed to fetch tool context.")
            context = 'Error: failed to fetch tool context.'
        context += "</tool_context>\n\n"
        print(f"queuing tool context result {context}")
        queue.put(context)
        return

    def get_tool_list(self):
        response = self.utils.invoke_lambda(
            self.tools_provider_fn,
            {
                "operation": "list_tools",
                "origin": self.my_origin,
                "args": {}
            }
        )
        body = json.loads(response['body'])
        print(f"response from get_tool_list: {body}")
        return body

    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = GenerationHandlerEvent().from_lambda_event(event)
        print(f"Got generationHandlerEvent {handler_evt.__dict__()}, type {type(handler_evt)}")
        method = handler_evt.method
        path = handler_evt.path

        status = 200
        user_id = None
        result = {}
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
            # if 'document_collections' in msg_obj:
            # first assemble the chat history and find a sensible set of
            # search terms given the most recent question
            msg_obj['user_id'] = user_id
            recommendations = self.get_orchestration(handler_evt)   
            print(f"Got recommendations: {recommendations}, type {type(recommendations)}")
            vector_search_recommendations = []
            graph_search_recommendations = []
            tool_recommendations = []
            result = ''

            if 'final_answer' in recommendations.keys() and \
                recommendations['final_answer']:
                result = recommendations['final_answer']
            else:
                for item_id in list(recommendations.keys()):
                    if 'tool_inputs' in recommendations[item_id].keys():
                        print(f"Found tool recommendation {recommendations[item_id]}")
                        tool_recommendations.append(recommendations[item_id])
                    else:
                        recommendation = recommendations[item_id]
                        if "search_terms" in recommendation and \
                            recommendation['search_terms'] not in ['',None,'None']:
                            vector_search_recommendations.append({
                                "id": item_id,
                                "search_terms": recommendation['search_terms']
                            })
                            
                        if "graph_database_query" in recommendation and\
                        recommendation['graph_database_query'] not in ['',None,'None']:
                            graph_search_recommendations.append({
                                "id": item_id,
                                "graph_database_query": recommendation['graph_database_query']
                            })

                context += self.get_context(
                    graph_search_recommendations,
                    vector_search_recommendations,
                    tool_recommendations
                )

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
                        "modelId": msg_obj['model']['model_id'], 
                        "messages": [{
                            "role": "user",
                            "content": [{
                                "text": prompt
                            }]
                        }], 
                        "inferenceConfig": model_args
                    },
                    self.my_origin
                )
                print(f"Got result from bedrock: {result}")
                if result["statusCode"] != 200:
                    raise Exception(f"Failed to invoke bedrock {result}")
                else:
                    result = result['response']
        response = self.utils.format_response(status, result, handler_evt.origin)
        print(f"generation_handler returning response {response}")
        return response

    def invoke_tool(self, tool_name, inputs):
        inputs['tool_name'] = tool_name
        print(f"generation_handler.invoke_tool invoking {self.tools_provider_fn}")
        response = self.utils.invoke_lambda(
            self.tools_provider_fn,
            {
                "operation": "invoke_tool",
                "origin": self.my_origin,
                "args": inputs
            }
        )
        print(f"Got invoke_tool response {response}")
        return json.loads(response['body'])

def handler(event, context):
    global generation_handler
    if not generation_handler:
        generation_handler = GenerationHandler()
    return generation_handler.handler(event, context)
