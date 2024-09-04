#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import jq
import json
import numpy as np
import os

from base64 import b64encode
from math import ceil
from numpy.linalg import norm
from os import getcwd, getenv, path
from pathlib import Path
# from queue import Queue
# from threading import Thread

from multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider_event import BedrockProviderEvent
from multi_tenant_full_stack_rag_application.utils import BotoClientProvider, invoke_service
# from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingType

"""
API

GET /bedrock_provider/...
        list_models: fetch list of foundation models available
        get_model_dimensions/{model_id}: fetch list of dimensions for a given model
        get_model_max_tokens/{model_id}: fetch max tokens for a given model

POST /bedrock_provider/...
        embed_text: embed the given text.
            body = {
                "operation": "embed_text",
                "args": {
                    # Cohere models only have one default dim, 1024, so this
                    # is only useful for Titan text embeddings v2, in
                    # which case it could be 1024 (default), 512, or 256.
                    'dimensions': int, optional, default 1024
                    # search_document is for ingestin and search_query is for 
                    # inference time. Only valid for Cohere models.
                    'input_type': ['search_document' or 'search_query'], (optional), defaults to search_query
                    'model_id': str, (required),
                    'text': str (required)
                }
            }
        invoke_model: send a payload to a bedrock model.
            body = {
                "operation": "embed_text",
                "args": {
                    'model_id': str (required),
                    'prompt': str (either prompt or messages are required). Used for non-Claude 3 models.
                    'model_kwargs': dict (optional), the keyword args to send to the model,
                    'messages': list of dicts (either prompt or messages are required). Used for Claude 3 models.
                        [{
                            "content": "the text or the binary image data you'd get from opening it 'rb' and doing a .read() on it",
                            "mime_type": "either 'text' or one of 'jpg', 'image/jpeg', 'png', 'image/png', 'png', 'image/webp', 'webp', 'image/gif', 'gif'
                        }]
                }
            }   
        get_semantic_similarity: given two text chunks, return a 
            similarity score between 0 and 1.
            body = {
                "operation": "embed_text",
                "args": {
                    'chunk_text': str, (required)
                    'dimensions': int, (optional) dimensions of the embedding model to use.
                    'model_id': str, (required) the embedding model to use.
                    'search_text': str, (required)
                }
            }
        get_token_count: return an estimated number of tokens in the given
            input text. Estimates by splitting into words and multiplying
            by 1.3 tokens per word to arrive at tokens. Fast and conservative
            estimate to avoid ingestion errors from too many tokens.
            body = {
                "operation": "embed_text",
                "args": {
                    text': str (required)
                }
            }
"""



bedrock_provider = None

parent_path = Path(__file__).parent.resolve()
params_path = path.join(parent_path, 'bedrock_model_params.json')


with open(params_path, 'r') as params_in:
    bedrock_model_params_json = params_in.read()
    # print(f"Got bedrock_model_params before parsing: {json.dumps(bedrock_model_params_json)}")
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
        bedrock_client = BotoClientProvider.get_client('bedrock'),
        bedrock_agent_client  = BotoClientProvider.get_client('bedrock-agent'),
        bedrock_agent_rt_client = BotoClientProvider.get_client('bedrock-agent-runtime'),
        bedrock_rt_client = BotoClientProvider.get_client('bedrock-runtime'),
        s3_client = BotoClientProvider.get_client('s3'),
        ssm_client = BotoClientProvider.get_client('ssm')
    ):
        self.bedrock = bedrock_client
        self.bedrock_agent = bedrock_agent_client
        self.bedrock_agent_rt = bedrock_agent_rt_client
        self.bedrock_rt = bedrock_rt_client
        self.model_params = bedrock_model_params
        self.s3 = s3_client
        self.ssm = ssm_client
        # frontend origins initialized lazily
        self.frontend_origins = None

    def embed_text(self, text, model_id, input_type='search_query', *, dimensions):
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
            print(f"Calling with model {model_id}, input {text},  kwargs {kwargs}")
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

    def get_frontend_origins():
        if not self.frontend_origins:
        origin_domain_name = self.ssm.get_parameter(
            Name=f'/{getenv("STACK_NAME")}/frontend_origin'
        )['Parameter']['Value']

        if not origin_domain_name.startswith('http'):
            origin_domain_name = 'https://' + origin_domain_name
        
        self.frontend_origins = [
            origin_domain_name
        ]
        return self.frontend_origins
    
    def get_model_dimensions(self, model_id):
        if 'dimensions' in self.model_params[model_id].keys():
            return self.model_params[model_id]['dimensions']
        else:
            return 0

    def get_model_max_tokens(self, model_id):
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
        self, search_text, chunk_text, model_id, dimensions
    ):
        s_emb = self.embed_text(search_text, model_id, dimensions=dimensions)
        c_emb = self.embed_text(chunk_text, model_id, dimensions=dimensions)
        return np.dot(s_emb, c_emb) / (norm(s_emb) * norm(c_emb))

    def get_token_count(self, input_text):
        # this provides a conservative estimate that tends
        # to overestimate number of tokens, so you'll have a 
        # buffer to stay under the token limits.
        return ceil(len(input_text.split()) * 1.3)

    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = BedrockProviderEvent().from_lambda_event(event)
        print(f"converted to handler_evt {handler_evt.__dict__}")
        method = handler_evt.method
        path = handler_evt.path
        if handler_evt.origin not in self.frontend_origins:
            return format_response(403, {}, None)
        
        status = 200
        user_id = None
        user_email = None
        if method == 'OPTIONS': 
            result = {}
        
        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            result = invoke_service('auth_provider', {}, handler_evt.auth_token)
            sys.exit()
            # # TODO change this with a call to the auth provider service
            # # user_id = self.auth_provider.get_userid_from_token(handler_evt.auth_token)
            # user_id = self.get_userid_from_token(handler_evt.auth_token)
            # print(f"Got user_id {user_id} from auth_token {handler_evt.auth_token}")
            # if not user_id:
            #     raise Exception("Failed to get user_id from the jwt sent in the event.")
            # handler_evt.user_id = user_id
        
        if handler_evt.method == 'GET':
            operation = handler_evt.operation

            if operation == 'get_model_dimensions':
                model_id = handler_evt.params['model_id']
                response = self.get_model_dimensions(model_id)
            
            elif operation == 'get_model_max_tokens':
                model_id = handler_evt.params['model_id']
                response = self.get_model_max_tokens(model_id)
            
            # elif operation == 'list_bedrock_kbs':
            #     response = self.list_bedrock_kbs()
            
            if operation == 'list_models':
                response = self.list_models()
            
            print(f"GET /bedrock_provider response = {response}")
            result = {
                "method": "GET /bedrock_provider",
                "path": handler_evt.path,
                "operation": handler_evt.operation,
                "response": response,
                "statusCode": 200
            }

        elif handler_evt.method == 'POST':
            operation = handler_evt.operation

            if operation == 'embed_text':
                model_id = handler_evt.body['model_id']
                text = handler_evt.body['input_text']
                dimensions = handler_evt.body['dimensions'] 
                response = self.embed_text(text, model_id, dimensions=dimensions)

            elif operation == 'get_semantic_similarity':
                search_text = handler_evt.body['search_text']
                chunk_text = handler_evt.body['chunk_text']
                model_id = handler_evt.body['model_id']
                dimensions = handler_evt.body['dimensions']
                response = self.get_semantic_similarity(search_text, chunk_text, model_id, dimensions)
            
            elif operation == 'get_token_count':
                input_text = handler_evt.body['input_text']
                response = self.get_token_count(input_text)
  
            elif operation == 'invoke_model':
                model_id = handler_evt.body['model_id']
                prompt = handler_evt.body['prompt'] if 'prompt' in handler_evt.body else ''
                model_kwargs = handler_evt.body['model_kwargs'] if 'model_kwargs' in handler_evt.body else {}
                messages = handler_evt.body['messages'] if 'messages' in handler_evt.body else []
                response = self.invoke_model(model_id, prompt, model_kwargs, messages=messages)
                print(f"invoke_model got response {response}")   
            
            # print(f"POST /bedrock_provider response = {response}")
            result = {
                "method": handler_evt.method,
                "path": handler_evt.path,
                "operation": handler_evt.operation,
                "response": response,
                "statusCode": 200
            }
    
        else:
            raise Exception(f'Unexpected method {handler_evt.method}')
        return result

    def invoke_model(self, model_id: str, prompt: str='', model_kwargs={}, *, messages=[]):
        # print(f"Invoking model {model_id}")
        content_type = 'application/json'
        accept = '*/*'
        print(f"Invoke model got model_kwargs {model_kwargs}")
        model_kwargs = self._populate_default_args(model_id, model_kwargs)
        print(f"After merging default args, model_kwargs = {model_kwargs}")

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
                        content_image = b64encode(msg["content"]).decode('utf8')
                        final_content.append({
                            "type": "image", 
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg", 
                                "data": content_image
                            }
                        })
                    else:
                        raise Exception(f"Unexpected mime type received: {msg['mime_type']}. If it's a plain text file (like code) pass in 'text/plain' as the mime type")
                
                args['messages'] = [{
                    "role": "user",
                    "content": final_content
                }]
            # print(f"Running with args['messages'] = {args['messages']}")
        else:
            args = model_kwargs
            args["prompt"] = prompt

        # print(f"invoking model with model_id {model_id} and args {args}")
        result = self.bedrock_rt.invoke_model(
            modelId=model_id,
            accept=accept,
            contentType=content_type,
            body=json.dumps(args)
        )
        body = json.loads(result['body'].read())

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