#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import jq
import json
import numpy as np
import os

from base64 import b64encode
from botocore.config import Config
from numpy.linalg import norm
from os import getcwd, getenv, path
from pathlib import Path
from queue import Queue
from threading import Thread
from tokenizers import Tokenizer

from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingType

s3 = boto3.client('s3')
# Until Bedrock provides a tokenizer we need to guess. I'm 
# using the cohere tokenizer, which counts slightly differently
# than the one for Titan, so multiplying by this modifier
# reduces the likelihood of a chunk being too big.
# titan_max_tokens_modifier = 0.9 
parent_path = Path(__file__).parent.resolve()
params_path = path.join(parent_path, 'bedrock_model_params.json')

config = Config(retries={"max_attempts": 10, "mode": "adaptive"})

with open(params_path, 'r') as params_in:
    bedrock_model_params_json = params_in.read()
    # print(f"Got bedrock_model_params before parsing: {json.dumps(bedrock_model_params_json, indent=2)}")
    bedrock_model_params = json.loads(bedrock_model_params_json)


class KBDocument:
    def __init__(self, 
        id: str,
        content: str,
        metadata: dict={}
    ):
        self.id = id
        self.content = content
        self.metadata = metadata
    
    def __str__(self):
        return_str = f"ID: {self.id},"
        if self.metadata != {}:
            return_str += f" METADATA: {self.metadata},"
        return_str += f" CONTENT: {self.content}" 
        return return_str
    
class BedrockProvider():
    def __init__(self,
        bedrock_client = boto3.client('bedrock', config=config),
        bedrock_agent_client  = boto3.client('bedrock-agent', config=config),
        bedrock_agent_rt_client = boto3.client('bedrock-agent-runtime', config=config),
        bedrock_rt_client = boto3.client('bedrock-runtime', config=config),
        s3_client = boto3.client('s3', config=config)
    ):
        self.bedrock = bedrock_client
        self.bedrock_agent = bedrock_agent_client
        self.bedrock_agent_rt = bedrock_agent_rt_client
        self.bedrock_rt = bedrock_rt_client
        self.model_params = bedrock_model_params
        self.s3 = s3_client
        self.tokenizer = Tokenizer.from_pretrained("Cohere/command-nightly")

    def embed_text(self, text, model_id, input_type=EmbeddingType.search_query, *, dimensions=None):
        if model_id.startswith('cohere'):
            kwargs = {'input_type': input_type.name}
            if dimensions: 
                kwargs['dimensions'] = dimensions

            return self.invoke_model(model_id, text, kwargs)
        else:
            return self.invoke_model(model_id, text)
    
    @staticmethod
    def extract_context(results):
        text = ''
        for kb_id in results:
            kb_results = results[kb_id]
            for result in kb_results:
                text += ' ' + result['content']['text']
                text += '\n\n'
        return text

    def get_model_dimensions(self, model_id):
        return self.model_params[model_id]['dimensions']

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
        self, search_text, chunk_text
    ):
        s_emb = self.embed_text(search_text)
        c_emb = self.embed_text(chunk_text)
        return np.dot(s_emb, c_emb) / (norm(s_emb) * norm(c_emb))

    def get_token_count(self, input_text):
        return len(self._tokenize(input_text)) - 1

    def invoke_model(self, model_id: str, prompt: str='', model_kwargs={}, *, messages=[]):
        # print(f"Invoking model {model_id}")
        content_type = 'application/json'
        accept = '*/*'
        model_kwargs = self.populate_default_args(model_id, model_kwargs)
        if model_id.startswith('amazon'):
            args = {
                "inputText": prompt
            }
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
    
    def list_bedrock_kbs(self):
        kbs = []
        args = {
        "maxResults": 100
        }
        while True:
            response = self.bedrock_agent.list_knowledge_bases(
                **args
            )

            for kb in response['knowledgeBaseSummaries']:
                if kb['status'] != 'ACTIVE':
                    continue
                kbs.append({
                    "id": kb['knowledgeBaseId'],
                    "name": kb['name'],
                    "description": kb['description']
                })
            if "nextToken" in response:
                args["nextToken"] = response["nextToken"]
            else:
                break

        return kbs        

    def list_models(self):
        if not hasattr(self, 'models'):
            self.models = self.bedrock.list_foundation_models()['modelSummaries']
        return self.models
    
    def populate_default_args(self, model_id, model_kwargs={}):
        params = self.model_params[model_id]
        paths = params['default_paths']
        args = {}
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

    def save_to_bedrock_kbs(docs: [KBDocument], s3_prefix, auto_sync=True) -> None: 
        for doc in docs:
            # call s3.put_object to save each doc to a file in s3
            s3.put_object(
                Bucket=getenv('S3_BUCKET'),
                Key=f"{s3_prefix}/{doc.id}",
                Body=doc,
                ContentType='text/plain'
            )

    def search_bedrock_kbs(self, prompt, kb_ids, top_k=10):
        in_queue = Queue(len(kb_ids))
        out_queue = Queue(len(kb_ids))
        if not isinstance(kb_ids, list):
            if isinstance(kb_ids, str):
                kb_ids = [kb_ids]
            else:
                raise Exception(f'invalid kb_ids passed in of type {type(kb_ids)}')

        for id in kb_ids:
            in_queue.put(id)
        # in_queue.put(None)
        q_len = in_queue.qsize()

        def consumer(in_queue, out_queue):
            while True:
                id = in_queue.get()
                results = {}
                args = {
                    'retrievalQuery': {
                        "text": prompt
                    },
                    "retrievalConfiguration": {
                        'vectorSearchConfiguration': {
                            'numberOfResults': top_k
                        }
                    }
                }
                next_token = None
                args['knowledgeBaseId'] = id
                results[id] = []
                while True:
                    if next_token: 
                        args['nextToken'] = next_token
                    response = self.bedrock_agent_rt.retrieve(
                        **args
                    )

                    results[id] += response['retrievalResults']
                    if 'nextToken' in response:
                        next_token = response['nextToken']
                    else:
                        break
                out_queue.put(results)
                in_queue.task_done()

        consumer = Thread(target=consumer, args=(in_queue, out_queue), daemon=True)
        consumer.start()
        in_queue.join()
        final_text = ''
        for i in range(out_queue.qsize()):
            result = out_queue.get()
            text = self.extract_context(result)
            final_text += text
        return final_text

    def _tokenize(self, input_text):
        encoding = self.tokenizer.encode(input_text)
        return encoding.ids
