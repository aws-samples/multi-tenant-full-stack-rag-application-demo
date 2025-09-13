#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import jq
import json
import os
import sys

from base64 import b64decode, b64encode
from math import ceil
from os import getcwd, getenv, path
from pathlib import Path
# from queue import Queue
# from threading import Thread

from multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider_event import BedrockProviderEvent
from multi_tenant_full_stack_rag_application.service_provider import ServiceProvider
from multi_tenant_full_stack_rag_application.service_provider_event import ServiceProviderEvent
from multi_tenant_full_stack_rag_application import utils

"""
API
event {
    "operation": [embed_text, get_model_dimensions, get_model_max_tokens, get_token_count, invoke_model, list_models ]
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

        for get_prompt:
            "prompt_id"

        for invoke_model:
            messages: [dict],
            model_id: str,
            additional_model_req_fields: any=None, 
            additional_model_resp_field_paths: [str]=None,
            guardrail_config: dict=None, 
            inference_config: dict={},
            system: list=None, 
            tool_config: dict=None
        
        for list_models:
                none
}
"""


bedrock_provider = None

parent_path = Path(__file__).parent.resolve()
params_path = path.join(parent_path, 'bedrock_model_params.json')


with open(params_path, 'r') as params_in:
    bedrock_model_params_json = params_in.read()
    # print(f"Got bedrock_model_params before parsing: {bedrock_model_params_json}")
    bedrock_model_params = json.loads(bedrock_model_params_json)

class BedrockProvider(ServiceProvider):
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
            args = {
                "texts":[text],
                "input_type": input_type
            }
            # kwargs = {'input_type': input_type}
            # if dimensions: 
            #     kwargs['dimensions'] = dimensions
            # return self.bedrock_rt.invoke_model(model_id, text, kwargs)
        elif model_id.startswith('amazon'):
            # kwargs = {
            #     'dimensions': dimensions
            # }
            # # print(f"Calling with model {model_id}, input {text},  kwargs {kwargs}")
            # return self.invoke_model(model_id, text, kwargs)
            args = {
                "inputText": text,
                "dimensions": dimensions
            }
        else:
            raise Exception("Unknown model ID provided.")
        body = json.dumps(args).encode('utf-8')
        
        response = self.bedrock_rt.invoke_model(
            modelId=model_id,
            body=body,
            contentType = 'application/json',
            accept='*/*'
        )
        print(f"embed_text got response from bedrock_rt.invoke_model: {response}")
        body = json.loads(response['body'].read())
        # print(f"embed_text result: {body.keys()}")
        # print(f"Got response from bedrock.invoke_model: {body}")
        return body['embedding']
        
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
            token_ct = self.model_params[model_id]['maxTokens']['max']
        # elif model_id.startswith('anthropic'):
        #     token_ct = self.model_params[model_id]['max_tokens_to_sample']['max']
        elif model_id.startswith('cohere.'):
            token_ct = self.model_params[model_id]['maxTokens']['max']
        elif model_id.startswith('meta.llama2'):
            token_ct = self.model_params[model_id]['max_gen_len']['max']
        elif model_id.startswith('stability.'):
            token_ct = self.model_params[model_id]['modelMaxTokens']
        else:
            raise Exception("Unknown model ID provided.")
        
        # if model_id.startswith('amazon.titan-embed'):
        #     token_ct = int(token_ct * titan_max_tokens_modifier)
        return token_ct
        
    def get_prompt(self, prompt_id, version="DRAFT"):
        return self.bedrock_agent.get_prompt(
            promptIdentifier=prompt_id,
            promptVersion=version
        )

    def handler(self, handler_evt: BedrockProviderEvent, context):
        print(f"Got event {handler_evt}")
        if not isinstance(handler_evt, BedrockProviderEvent):
            handler_evt = BedrockProviderEvent(**handler_evt)
        print(f"handler_evt is now {handler_evt}, {type(handler_evt)}")
        if not self.allowed_origins:
            self.allowed_origins = self.utils.get_allowed_origins()
        
        status = 200
        operation = handler_evt.operation

        if handler_evt.origin not in self.allowed_origins.values():
            status = 403
            response = "forbidden"
        
        elif operation == 'embed_text':
            model_id = handler_evt.args['model_id']
            text = handler_evt.args['input_text']
            dimensions = handler_evt.args['dimensions']
            response = self.embed_text(text, model_id, dimensions=dimensions)
        
        elif operation == 'get_model_dimensions':
            response = self.get_model_dimensions(handler_evt.args['model_id'])
        
        elif operation == 'get_model_max_tokens':
            response = self.get_model_max_tokens(handler_evt.args['model_id'])

        elif operation == 'get_prompt':
            response = self.get_prompt(handler_evt.args['prompt_id'])

        elif operation == 'get_token_count':
            input_text = handler_evt.args['input_text']
            response = self.get_token_count(input_text)

        elif operation == 'invoke_model':
            model_id = handler_evt.args['model_id']
            inference_config = handler_evt.args['inference_config'] or {}
            messages = handler_evt.args['messages'] or []
            response = self.invoke_model(
                inference_config=inference_config,
                messages=messages,
                model_id=model_id,
            )
            
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
        
    def invoke_model(self, *, 
        messages: [dict], 
        model_id: str, 
        additional_model_req_fields: any=None, 
        additional_model_resp_field_paths: [str]=None,
        guardrail_config: dict=None, 
        inference_config: dict={},
        system: list=None, 
        tool_config: dict=None
    ):
        content_type = 'application/json'
        accept = '*/*'
        inference_config = self._populate_default_args(model_id, inference_config)
        print(f"After merging default args, inference_config = {inference_config}")
        final_msgs = []
        for msg in messages:
            print(f"msg type: {type(msg)}")
            if isinstance(msg, str):
                msg = json.loads(msg)
            print(msg)
            print(msg.keys())
            for i in range(len(msg['content'])):
                print(f"message content array: {msg['content']}")
                print(f"type(msg[content][i]) {type(msg['content'][i])}")
                if isinstance(msg['content'][i], str):
                    print("Loading json string.")
                    msg['content'][i] = json.loads(msg['content'][i])
                if 'image' in msg['content'][i].keys():
                    print(f"image dict: {msg['content'][i]['image']}")
                    print(f"image dict type: {type(msg['content'][i]['image'])}")
                    print(f"src dict type: {type(msg['content'][i]['image']['source'])}")
                    print(msg['content'][i]['image']['source'])
                    if isinstance(msg['content'][i]['image']['source']['bytes'], str):
                        print("Converting content payload from string to bytes.")
                        msg['content'][i]['image']['source']['bytes'] = b64decode(msg['content'][i]['image']['source']['bytes'].encode('utf-8'))
            final_msgs.append(msg)
        args = {
            "modelId": model_id,
            "messages": final_msgs,
            "inferenceConfig": inference_config
        }

        if additional_model_req_fields:
            args['additionalModelRequestFields'] = additional_model_req_fields
        
        if additional_model_resp_field_paths:
            args['additionalModelResponseFieldPaths']

        if guardrail_config:
            args['guardrailConfig'] = guardrail_config

        if system:
            args['system'] = system
        
        if tool_config:
            args['toolConfig'] = tool_config
    
        response = self.bedrock_rt.converse(**args)
        print(f"invoke_model got response from bedrock_rt.invoke_model: {response}")
        return response['output']['message']['content'][0]['text']
        # body = json.loads(response['body'].read())
        # print(f"Invocation result: {body}")
        # print(f"Got response from bedrock.converse: {body}")
        # return body

        # if model_id.startswith('amazon'):
        #     args = {
        #         "inputText": prompt,
        #     }
        #     if 'dimensions' in model_kwargs.keys():
        #         args['dimensions'] = model_kwargs['dimensions']
        #     if "embed" not in model_id:
        #         args["textGenerationConfig"] = model_kwargs
        # elif model_id.startswith('cohere.embed'):
        #     args = {
        #         "texts": [prompt],
        #         "input_type": model_kwargs["input_type"]
        #     }
        # elif model_id.startswith('anthropic.claude-3'):
        #     args = model_kwargs
        #     if len(messages) == 0:
        #         args['messages'] = [
        #             {"role": "user", "content": prompt}
        #         ]
        #     else: 
        #         # format should be [{"mime_type": mime_type, "content": content}]
        #         # for images content should be bytes.
        #         final_content = []
        #         for msg in messages:
        #             print(f"Got message with mime type {msg['mime_type']}")
        #             if msg["mime_type"] in ['text/plain','text', 'txt']:
        #                 final_content.append({
        #                     "type": "text",
        #                     "text": msg["content"]
        #                 })
        #             elif msg["mime_type"] in [
        #                 "jpg",
        #                 "image/jpeg",
        #                 "png",
        #                 "image/png",
        #                 "png",
        #                 "image/webp",
        #                 "webp",
        #                 "image/gif"
        #                 "gif"
        #             ]:   
        #                 # content_image = msg["content"].encode('utf-8')
        #                 print(f"Type of msg content is now {type(msg['content'])}")
        #                 final_content.append({
        #                     "type": "image", 
        #                     "source": {
        #                         "type": "base64",
        #                         "media_type": "image/jpeg", 
        #                         "data": msg["content"]
        #                     }
        #                 })
        #             else:
        #                 raise Exception(f"Unexpected mime type received: {msg['mime_type']}. If it's a plain text file (like code) pass in 'text/plain' as the mime type")
                
        #         args['messages'] = [{
        #             "role": "user",
        #             "content": final_content
        #         }]
        #     # # print(f"Running with args['messages'] = {args['messages']}")
        # else:
        #     args = model_kwargs
        #     args["prompt"] = prompt

        # print(f"invoking model with model_id {model_id} and args {args}")
        # result = self.bedrock_rt.invoke_model(
        #     modelId=model_id,
        #     accept=accept,
        #     contentType=content_type,
        #     body=json.dumps(args)
        # )
        # body = json.loads(result['body'].read())
        # print(f"Invocation result: {body}")
        # if "content" in body:
        #     text = ''
        #     for line in body['content']:
        #         if line['type'] == 'text':
        #             text += line['text']
        #     return text
        # elif "completion" in body: 
        #     return body['completion']
        # elif "generations" in body:
        #     text = ''
        #     for result in body['generations']:
        #         text += result['text']
        #     return text
        # elif "results" in body:
        #     text = ''
        #     for result in body['results']:
        #         text += result['outputText']
        #     return text 
        # elif "embedding" in body:
        #     return body['embedding']
        # elif "embeddings" in body:
        #     return body["embeddings"]
        # elif "outputs" in body:
        #     text = ''
        #     for output in body['outputs']:
        #         text += output['text']
        #     return text
        # else:
        #     raise Exception('could not find return value in payload!')
    
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
    
    def _populate_default_args(self, model_id, inference_config={}):
        params = None
        alt_model_id = model_id.replace('us.', '')
        if model_id in self.model_params:
            params = self.model_params[model_id]
        elif alt_model_id in self.model_params:
            params = self.model_params[alt_model_id]
        else:
            raise Exception(f"Could not find model {model_id} or {alt_model_id} in models.")
        
        paths = params['default_paths']
        args = {
            **inference_config
        }
        for path in paths:
            parts = path.split('.')
            if len(parts) > 1:
                key = parts[-2]
            else: 
                key = parts[0]
    
            if key in inference_config:
                args[key] = inference_config[key]
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


def handler(event: BedrockProviderEvent, context):
    global bedrock_provider
    if not bedrock_provider:
        bedrock_provider = BedrockProvider()
    
    return bedrock_provider.handler(event, context)
