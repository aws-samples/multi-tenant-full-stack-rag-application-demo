#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import jq
import json
import numpy as np
import os
import sys

from base64 import b64encode
from math import ceil
from numpy.linalg import norm
from os import getcwd, getenv, path
from pathlib import Path
# from queue import Queue
# from threading import Thread

from multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider_event import BedrockProviderEvent
from multi_tenant_full_stack_rag_application import utils  

"""
API
event {
    "operation": [embed_text, get_model_dimensions, get_model_max_tokens, get_semantic_similarity, get_token_count, invoke_model, list_models ]
    "origin": the function name of the calling function, or the frontend_origin.,
    "args": 
        for embed_text:
            "model_id": str,
            "input_text": str,
            "dimensions": int=1024,
            "input_type": str="search_query",

        for get_model_dimensions:
            "model_id": str

        for get_model_max_tokens:
            "model_id": str

        for get_semantic_similarity:
            "chunk_text": str,
            "model_id": str,
            "search_text": str,
            "dimensions": int=1024,
            "input_type": "search_query"

        for invoke_model:
            "model_id": str,
            "prompt": str='',
            "model_kwargs": dict={}
            "messages": [dict]=[]

        for list_models:
            none



}
"""


bedrock_provider = None

parent_path = Path(__file__).parent.resolve()
params_path = path.join(parent_path, 'bedrock_model_params.json')


with open(params_path, 'r') as params_in:
    bedrock_model_params_json = params_in.read()
    # # print(f"Got bedrock_model_params before parsing: {json.dumps(bedrock_model_params_json)}")
    bedrock_model_params = json.loads(bedrock_model_params_json)


# class KBDocument:
#     def __init__(self, 
#         id: str,
#         content: str,
#         metadata: dict={}
#     ):
#         self.id = id
#         self.content = content
#         self.metadata = metadata
    
#     def __str__(self):
#         return_str = f"ID: {self.id},"
#         if self.metadata != {}:
#             return_str += f" METADATA: {self.metadata},"
#         return_str += f" CONTENT: {self.content}" 
#         return return_str
    
class BedrockProvider():
    def __init__(self,
        bedrock_client = None,
        bedrock_agent_client  = None,
        bedrock_agent_rt_client = None,
        bedrock_rt_client = None,
        # cognito_identity_client = None,
        ssm_client = None
    ):
        self.utils = utils
        if not bedrock_client:
            self.bedrock = utils.get_bedrock_client()
        else:
            # print("Used br client passed in.")
            self.bedrock = bedrock_client
        
        if not bedrock_agent_client:
            self.bedrock_agent = utils.get_bedrock_agent_client()
        else:
            # print("Used bra client passed in.")
            self.bedrock_agent = bedrock_agent_client
        
        if not bedrock_agent_rt_client:
            self.bedrock_agent_rt = utils.get_bedrock_agent_runtime_client()
        else:
            # print("Used brart client passed in.")
            self.bedrock_agent_rt = bedrock_agent_rt_client
        
        if not bedrock_rt_client:
            self.bedrock_rt = utils.get_bedrock_runtime_client()
        else:
            # print("Used brt client passed in.")
            self.bedrock_rt = bedrock_rt_client
        
        # if not cognito_identity_client:
        #     self.cognito = utils.BotoClientProvider.get_client('cognito-identity')
        # else:
        #     # print("Used cognito identity client passed in")
        #     self.cognito = cognito_identity_client

        if not ssm_client:
            self.ssm = utils.BotoClientProvider.get_client('ssm')
        else:
            # print("Used ssm client passed in")
            self.ssm = ssm_client

        self.model_params = bedrock_model_params
        self.stack_name = os.getenv('STACK_NAME')
        print(f"Bedrock_provider loaded with stack_name {self.stack_name}")
        self.ssm_params = self.utils.get_ssm_params(ssm_client=ssm_client)
        self.allowed_origins = self.utils.get_allowed_origins()
        print(f"Got allowed_origins {self.allowed_origins}")
    
    def embed_text(self, text, model_id, input_type='search_query', *, dimensions=1024):
        print(f"Embedding text with model {model_id} and dimensions {dimensions}")
        if model_id.startswith('cohere'):
            kwargs = {'input_type': input_type}
            if dimensions: 
                kwargs['dimensions'] = dimensions
            return self.invoke_model(model_id, text, kwargs)
        elif model_id.startswith('amazon'):
            kwargs = {
                'dimensions': dimensions
            }
            # print(f"Calling with model {model_id}, input {text},  kwargs {kwargs}")
            return self.invoke_model(model_id, text, kwargs)
        else:
            raise Exception("Unknown model ID provided.")
    
    # @staticmethod
    # def extract_context(results):
    #     text = ''
    #     for kb_id in results:
    #         kb_results = results[kb_id]
    #         for result in kb_results:
    #             text += ' ' + result['content']['text']
    #             text += '\n\n'
    #     return text

    # def get_allowed_origins(self):
    #     if not self.allowed_origins:
    #         self.allowed_origins = [
    #             self.ssm_params['origin_frontend']
    #         ]
    #     return self.allowed_origins
    
    def get_model_dimensions(self, model_id):
        if 'dimensions' in self.model_params[model_id].keys():
            return self.model_params[model_id]['dimensions']
        else:
            return 0

    def get_model_max_tokens(self, model_id):
        if not model_id:
            raise Exception("bedrock_provider.get_model_max_tokens received null model_id.")
        
        if model_id.startswith('ai21.') or \
            model_id.startswith('amazon.titan-image-generator') or \
            model_id.startswith('amazon.titan-embed'): 
            token_ct = self.model_params[model_id]['maxTokens']['max']
        elif model_id.startswith('amazon.titan-text'):
            token_ct = self.model_params[model_id]['textGenerationConfig']['maxTokenCount']['max']
        elif model_id.startswith('anthropic.claude-3'):
            token_ct = self.model_params[model_id]['max_tokens']['max']
        elif model_id.startswith('anthropic'):
            token_ct = self.model_params[model_id]['max_tokens_to_sample']['max']
        elif model_id.startswith('cohere.'):
            token_ct = self.model_params[model_id]['max_tokens']['max']
        elif model_id.startswith('meta.llama2'):
            token_ct = self.model_params[model_id]['max_gen_len']['max']
        elif model_id.startswith('stability.'):
            token_ct = self.model_params[model_id]['modelMaxTokens']
        else:
            raise Exception("Unknown model ID provided.")
        
        # if model_id.startswith('amazon.titan-embed'):
        #     token_ct = int(token_ct * titan_max_tokens_modifier)
        return token_ct
        
    # only supports cosine similarity currently
    def get_semantic_similarity(
        self, search_text, chunk_text, model_id, dimensions, *, input_type='search_query'
    ):
        s_emb = self.embed_text(search_text, model_id, input_type, dimensions=dimensions)
        c_emb = self.embed_text(chunk_text, model_id, input_type, dimensions=dimensions)
        return np.dot(s_emb, c_emb) / (norm(s_emb) * norm(c_emb))

    # def get_token_count(self, input_text):
    #     # this provides a conservative estimate that tends
    #     # to overestimate number of tokens, so you'll have a 
    #     # buffer to stay under the token limits.
    #     return ceil(len(input_text.split()) * 1.3)

    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = BedrockProviderEvent().from_lambda_event(event)
        # print(f"converted to handler_evt {handler_evt.__dict__}")
        
        if not self.allowed_origins:
            self.allowed_origins = self.utils.get_allowed_origins()
        
        status = 200
        operation = handler_evt.operation

        if handler_evt.origin not in self.allowed_origins.values():
            status = 403
            response = "forbidden"
        
        elif operation == 'embed_text':
            model_id = handler_evt.model_id
            text = handler_evt.input_text
            dimensions = handler_evt.dimensions
            response = self.embed_text(text, model_id, dimensions=dimensions)
        
        elif operation == 'get_model_dimensions':
            model_id = handler_evt.model_id
            response = self.get_model_dimensions(model_id)
        
        elif operation == 'get_model_max_tokens':
            model_id = handler_evt.model_id
            response = self.get_model_max_tokens(model_id)

        elif operation == 'get_semantic_similarity':
            search_text = handler_evt.search_text
            chunk_text = handler_evt.chunk_text
            model_id = handler_evt.model_id
            dimensions = handler_evt.dimension
            response = self.get_semantic_similarity(search_text, chunk_text, model_id, dimensions)
        
        elif operation == 'get_token_count':
            input_text = handler_evt.input_text
            response = self.get_token_count(input_text)

        elif operation == 'invoke_model':
            model_id = handler_evt.model_id
            prompt = handler_evt.prompt if hasattr(handler_evt,'prompt')  else ''
            model_kwargs = handler_evt.model_kwargs if hasattr(handler_evt,'model_kwargs') else {}
            messages = handler_evt.messages if hasattr(handler_evt,'messages') else []
            response = self.invoke_model(model_id, prompt, model_kwargs, messages=messages)
            # print(f"invoke_model got response {response}")   
            
        elif operation == 'list_models':
            response = self.list_models()

        else: 
            raise Exception(f"Unknown operation {operation}")

        result = {
            "statusCode": status,
            "operation": handler_evt.operation,
            "response": response,
        }
        print(f"Bedrock_provider returning result {result}") 
        return result

    def invoke_model(self, model_id: str, prompt: str='', model_kwargs={}, *, messages=[]):
        # # print(f"Invoking model {model_id}")
        content_type = 'application/json'
        accept = '*/*'
        # print(f"Invoke model got model_kwargs {model_kwargs}")
        model_kwargs = self._populate_default_args(model_id, model_kwargs)
        # print(f"After merging default args, model_kwargs = {model_kwargs}")

        if model_id.startswith('amazon'):
            args = {
                "inputText": prompt,
            }
            if 'dimensions' in model_kwargs.keys():
                args['dimensions'] = model_kwargs['dimensions']
            if "embed" not in model_id:
                args["textGenerationConfig"] = model_kwargs
        elif model_id.startswith('cohere.embed'):
            args = {
                "texts": [prompt],
                "input_type": model_kwargs["input_type"]
            }
        elif model_id.startswith('anthropic.claude-3'):
            args = model_kwargs
            if len(messages) == 0:
                args['messages'] = [
                    {"role": "user", "content": prompt}
                ]
            else: 
                # format should be [{"mime_type": mime_type, "content": content}]
                # for images content should be bytes.
                final_content = []
                for msg in messages:
                    print(f"Got message with mime type {msg['mime_type']}")
                    if msg["mime_type"] in ['text/plain','text', 'txt']:
                        final_content.append({
                            "type": "text",
                            "text": msg["content"]
                        })
                    elif msg["mime_type"] in [
                        "jpg",
                        "image/jpeg",
                        "png",
                        "image/png",
                        "png",
                        "image/webp",
                        "webp",
                        "image/gif"
                        "gif"
                    ]:   
                        # content_image = msg["content"].encode('utf-8')
                        print(f"Type of msg content is now {type(msg['content'])}")
                        final_content.append({
                            "type": "image", 
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg", 
                                "data": msg["content"]
                            }
                        })
                    else:
                        raise Exception(f"Unexpected mime type received: {msg['mime_type']}. If it's a plain text file (like code) pass in 'text/plain' as the mime type")
                
                args['messages'] = [{
                    "role": "user",
                    "content": final_content
                }]
            # # print(f"Running with args['messages'] = {args['messages']}")
        else:
            args = model_kwargs
            args["prompt"] = prompt

        print(f"invoking model with model_id {model_id} and args {args}")
        result = self.bedrock_rt.invoke_model(
            modelId=model_id,
            accept=accept,
            contentType=content_type,
            body=json.dumps(args)
        )
        body = json.loads(result['body'].read())
        print(f"Invocation result: {body}")
        if "content" in body:
            text = ''
            for line in body['content']:
                if line['type'] == 'text':
                    text += line['text']
            return text
        elif "completion" in body: 
            return body['completion']
        elif "generations" in body:
            text = ''
            for result in body['generations']:
                text += result['text']
            return text
        elif "results" in body:
            text = ''
            for result in body['results']:
                text += result['outputText']
            return text 
        elif "embedding" in body:
            return body['embedding']
        elif "embeddings" in body:
            return body["embeddings"]
        elif "outputs" in body:
            text = ''
            for output in body['outputs']:
                text += output['text']
            return text
        else:
            raise Exception('could not find return value in payload!')
    
    # def list_bedrock_kbs(self):
    #     kbs = []
    #     args = {
    #     "maxResults": 100
    #     }
    #     while True:
    #         response = self.bedrock_agent.list_knowledge_bases(
    #             **args
    #         )

    #         for kb in response['knowledgeBaseSummaries']:
    #             if kb['status'] != 'ACTIVE':
    #                 continue
    #             kbs.append({
    #                 "id": kb['knowledgeBaseId'],
    #                 "name": kb['name'],
    #                 "description": kb['description']
    #             })
    #         if "nextToken" in response:
    #             args["nextToken"] = response["nextToken"]
    #         else:
    #             break

    #     return kbs        

    def list_models(self):
        if not hasattr(self, 'models'):
            self.models = self.bedrock.list_foundation_models()['modelSummaries']
        return self.models
    
    def _populate_default_args(self, model_id, model_kwargs={}):
        params = self.model_params[model_id]
        paths = params['default_paths']
        args = {
            **model_kwargs
        }
        for path in paths:
            parts = path.split('.')
            if len(parts) > 1:
                key = parts[-2]
            else: 
                key = parts[0]
    
            if key in model_kwargs:
                args[key] = model_kwargs[key]
            else:
                args[key] = jq.compile(f'.{path}').input_value(params).first()
        return args

    # TODO temporarily not integrated with the rest of the code
    # def save_to_bedrock_kbs(docs: [KBDocument], s3_prefix, auto_sync=True) -> None: 
    #     for doc in docs:
    #         # call s3.put_object to save each doc to a file in s3
    #         s3.put_object(
    #             Bucket=getenv('S3_BUCKET'),
    #             Key=f"{s3_prefix}/{doc.id}",
    #             Body=doc,
    #             ContentType='text/plain'
    #         )

    # TODO temporarily not integrated with the rest of the code
    # def search_bedrock_kbs(self, prompt, kb_ids, top_k=10):
    #     in_queue = Queue(len(kb_ids))
    #     out_queue = Queue(len(kb_ids))
    #     if not isinstance(kb_ids, list):
    #         if isinstance(kb_ids, str):
    #             kb_ids = [kb_ids]
    #         else:
    #             raise Exception(f'invalid kb_ids passed in of type {type(kb_ids)}')

    #     for id in kb_ids:
    #         in_queue.put(id)
    #     # in_queue.put(None)
    #     q_len = in_queue.qsize()

    #     def consumer(in_queue, out_queue):
    #         while True:
    #             id = in_queue.get()
    #             results = {}
    #             args = {
    #                 'retrievalQuery': {
    #                     "text": prompt
    #                 },
    #                 "retrievalConfiguration": {
    #                     'vectorSearchConfiguration': {
    #                         'numberOfResults': top_k
    #                     }
    #                 }
    #             }
    #             next_token = None
    #             args['knowledgeBaseId'] = id
    #             results[id] = []
    #             while True:
    #                 if next_token: 
    #                     args['nextToken'] = next_token
    #                 response = self.bedrock_agent_rt.retrieve(
    #                     **args
    #                 )

    #                 results[id] += response['retrievalResults']
    #                 if 'nextToken' in response:
    #                     next_token = response['nextToken']
    #                 else:
    #                     break
    #             out_queue.put(results)
    #             in_queue.task_done()

    #     consumer = Thread(target=consumer, args=(in_queue, out_queue), daemon=True)
    #     consumer.start()
    #     in_queue.join()
    #     final_text = ''
    #     for i in range(out_queue.qsize()):
    #         result = out_queue.get()
    #         text = self.extract_context(result)
    #         final_text += text
    #     return final_text


def handler(event, context):
    global bedrock_provider
    if not bedrock_provider:
        bedrock_provider = BedrockProvider()
    
    return bedrock_provider.handler(event, context)