#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth
from math import ceil

from .boto_client_provider import BotoClientProvider

sanitize_attributes = ['user_id', 'shared_by_userid', 'shared_with_userid']

bedrock_agent_client_singleton = None
bedrock_agent_runtime_client_singleton = None
bedrock_client_singleton = None
bedrock_runtime_client_singleton = None

lambda_client_singleton = None
s3_client_singleton = None
sqs_client_singleton = None
ssm_client_singleton = None
ssm_params = None
stack_name = os.getenv('STACK_NAME')

# def delete_sqs_message(rcpt_handle:str, queue_url: str, *, sqs_client=None): 
#     if not sqs_client:
#         if not sqs_client_singleton:
#             sqs_client_singleton = BotoClientProvider.get_client('sqs')
    
#     sqs_client = sqs_client_singleton
    
#     try: 
#         sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=rcpt_handle)
#     except Exception as e:
#         # print(f"e.args[0] == {e.args[0]}")
#         if "NonExistentQueue" in e.args[0]:
#             # print("CAUGHT ERROR due to non-existent queue in dev")
#         elif "ReceiptHandleIsInvalid" in e.args[0]:
#             # print("CAUGHT ERROR due to non-existent receipt handle in dev.")            
#         else:
#             raise Exception(f'Error occurred while deleting message: {e.args[0]}')

def delete_ingestion_status(user_id, doc_id, origin, *, delete_from_s3=False):
    return invoke_lambda(
        get_ssm_params('ingestion_status_provider_function_name'),
        {
            "operation": "delete_ingestion_status",
            "origin": origin,
            "args": {
                "user_id": user_id,
                "doc_id": doc_id,
                "delete_from_s3": delete_from_s3
            }
        }
    )

def embed_text(text, model_id, origin, *, dimensions=1024, lambda_client=None):
    response = invoke_lambda(
        get_ssm_params('embeddings_provider_function_name'),
        {
            'operation': 'embed_text',
            'origin': origin, 
            'args': {
                'input_text': text,
                'model_id': model_id,
                'dimensions': dimensions
            }
        }, 
        lambda_client=lambda_client
    )
    # print(f"utils.embed_text got response {response}") 
    return response


def format_response(status, body, origin, *, dont_sanitize_fields=[]):
    # print(f"format_response got status {status}, body {body}, origin {origin}")
    body = sanitize_response(body, dont_sanitize_fields=dont_sanitize_fields)
    response = {
        'statusCode': str(status),
        'headers': {
            'Access-Control-Allow-Headers': 'Authorization, Content-Type, x-csrf-token, X-Api-Key, *',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'DELETE,OPTIONS,GET,POST,PUT',
            'Vary': 'Origin'
        },
        'body': json.dumps(body)
    }
    # print(f"Returning response {response}")
    return response 


def get_allowed_origins():
    return get_ssm_params('origin_')


def get_bedrock_agent_client():
    global bedrock_agent_client_singleton
    if not bedrock_agent_client_singleton:
        bedrock_agent_client_singleton = BotoClientProvider.get_client('bedrock-agent')
    return bedrock_agent_client_singleton


def get_bedrock_agent_runtime_client():
    global bedrock_agent_runtime_client_singleton
    if not bedrock_agent_runtime_client_singleton:
        bedrock_agent_runtime_client_singleton = BotoClientProvider.get_client('bedrock-agent-runtime')
    return bedrock_agent_runtime_client_singleton


def get_bedrock_client():
    global bedrock_client_singleton
    if not bedrock_client_singleton:
        bedrock_client_singleton = BotoClientProvider.get_client('bedrock')
    return bedrock_client_singleton


def get_bedrock_runtime_client():
    global bedrock_runtime_client_singleton
    if not bedrock_runtime_client_singleton:
        bedrock_runtime_client_singleton = BotoClientProvider.get_client('bedrock-runtime')
    return bedrock_runtime_client_singleton


# def get_creds_from_token(user_id, auth_token, lambda_client=None):
#     global lambda_client_singleton
#     if not lambda_client:
#         if not lambda_client_singleton:
#             lambda_client_singleton = BotoClientProvider.get_client('lambda')
#         lambda_client = lambda_client_singleton
#     auth_provider_fn = get_ssm_params('auth_provider_function_name')
#     payload = {
#         "auth_token": auth_token,
#         "operation": 'get_creds_from_token',
#         "user_id": user_id,
#     }
#     response = invoke_lambda(auth_provider_fn, payload, lambda_client=lambda_client)
#     # print(f"get_creds_from_token got response {response}")
#     body = json.loads(response['body'])
#     return body['creds']

def get_document_collection(collection_id, user_id, *, account_id=None, lambda_client=None):
    global lambda_client_singleton
    if not account_id:
        account_id = os.getenv('AWS_ACCOUNT_ID')
    if not lambda_client:
        if not lambda_client_singleton:
            lambda_client_singleton = BotoClientProvider.get_client('lambda')
        lambda_client = lambda_client_singleton
    doc_collections_fn_name = get_ssm_params('document_collections_handler_function_name')
    response = lambda_client.invoke(
        FunctionName=doc_collections_fn_name, 
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "requestContext": {
                "accountId": account_id,
            }, 
            "headers": {
                # "authorization": f"Bearer {jwt}",
                "origin": get_ssm_params('origin_frontend')
            },
            "routeKey": "GET /document_collections",
            "body": {
                "collection_id": collection_id,
                "user_id": user_id
            }
        }).encode('utf-8')
    )
    # print(f"get_document_collection got response {response}")
    payload = json.loads(response['Payload'].read().decode('utf-8'))
    # print(f"Got payload {payload}")
    result = None
    dcs = json.loads(payload['body'])['response']
    
    for dc_name in list(dcs.keys()):
        collection = dcs[dc_name]
        if collection['collection_id'] == collection_id:
            result = collection
            break
    return result
        

def get_identity_pool_id():
    return get_ssm_params('identity_pool_id')


def  get_model_max_tokens(model_id, origin):
    fn_name = get_ssm_params('embeddings_provider_function_name')
    return invoke_lambda(
        fn_name,
        {
            "operation": "get_model_max_tokens",
            "origin": origin,
            "args": {
                "model_id": model_id
            }
        }
    )


def get_prompt_template(template_id, user_id, origin, *, account_id=None, lambda_client=None):
    global lambda_client_singleton
    if not lambda_client:
        if not lambda_client_singleton:
            lambda_client_singleton = BotoClientProvider.get_client('lambda')
        lambda_client = lambda_client_singleton
    if not account_id:
        account_id = os.getenv('AWS_ACCOUNT_ID')
    prompt_handler_fn_name = get_ssm_params('prompt_template_handler_function_name')
    
    response = invoke_lambda(
        prompt_handler_fn_name,
        {
            "requestContext": {
                "accountId": account_id,
            },
            "headers": {
                "origin": origin,
            },
            "routeKey": "GET /prompt_templates",
            "body": {
                "template_id": template_id,
                "user_id": user_id
            }
        },
        lambda_client=lambda_client
    )
    # print(f"get_prompt_template got response from lambda {response}")
    return response

def get_s3_client():
    global s3_client_singleton
    if not s3_client_singleton:
        s3_client_singleton = BotoClientProvider.get_client('s3')
    return s3_client_singleton


def get_ssm_client():
    global ssm_client_singleton
    if not ssm_client_singleton:
        ssm_client_singleton = BotoClientProvider.get_client('ssm')
    return ssm_client_singleton


# use without a param to get all params in the 
# stack
def get_ssm_params(param=None,*, ssm_client=None):
    global ssm_params
    if not ssm_client:
        ssm_client = get_ssm_client()
    # print(f"Stack name is {stack_name}")
    if not ssm_params:  
        ssm_params = {}
        next_token = ''
        path =  f"/{stack_name}"
        # print(f"Getting all params with prefix {path}")
        while next_token != None:
            args = {
                "Path": path,
                "Recursive": True,
                "MaxResults": 10,
            }
            if next_token != '':
                args['NextToken'] = next_token
            response = ssm_client.get_parameters_by_path(**args)
            # print(f"get_parameters_by_path response = {response}")
            for p in response['Parameters']:
                name = p['Name'].replace(f'/{stack_name}/', '')
                if name == 'origin_frontend' and \
                    not p['Value'].startswith('http'):
                    p['Value'] = 'https://' + p['Value']
                ssm_params[name] = p['Value']
            if 'NextToken' in response.keys():
                next_token = response['NextToken']
            else:
                next_token = None
    # print(f"Params are now {ssm_params}")
    if param:
        # print(f"Got here and param is {param}")
        return_vals = {}
        for param_name in ssm_params:
            if param_name.startswith(param):
                return_vals[param_name] = ssm_params[param_name]
        
        if len(return_vals.keys()) == 0:
            return None
        elif len(return_vals.keys()) == 1:
            return return_vals[list(return_vals.keys())[0]]
        else:
            return return_vals
    else:
        # print(f"Returning all params")
        return ssm_params


def get_token_count(text):
    return ceil(len(text.split())* 1.3)


def get_userid_from_token(auth_token, origin, *, lambda_client=None ):
    if not auth_token:
        return None
    global lambda_client_singleton
    # print(f"Getting userid from token {auth_token}")
    if not lambda_client:
        if not lambda_client_singleton:
            lambda_client_singleton = BotoClientProvider.get_client('lambda')
        lambda_client = lambda_client_singleton
    auth_provider_fn = get_ssm_params('auth_provider_function_name')

    payload = {
        "operation": "get_userid_from_token",
        "origin": origin,
        "args": {
            "auth_token": auth_token,
        }
    }
    # print(f"About to invoke lambda {auth_provider_fn} with payload {payload}") 
    response = invoke_lambda(
        auth_provider_fn, 
        payload, 
        lambda_client=lambda_client
    )
    # print(f"get_userid_from_token got response {response}")
    if "errorMessage" in response:
        raise Exception(response["errorMessage"])
    body = json.loads(response['body'])
    return body['user_id']
    

def get_user_pool_id():
    return get_ssm_params('user_pool_id')


def invoke_bedrock(operation, kwargs, origin):
    response = invoke_lambda(
        get_ssm_params('bedrock_provider_function_name'),
        {
            "operation": operation,
            "origin": origin,
            "args": kwargs
        },
    )
    # print(f"Got response from lambda {response}")
    return response


def invoke_lambda(function_name, payload={}, *, lambda_client=None):
    global lambda_client_singleton
    if not lambda_client:
        if not lambda_client_singleton:
            lambda_client_singleton = BotoClientProvider.get_client('lambda')
        lambda_client = lambda_client_singleton

    # print(f"Invoking {function_name}")
    print(f"Payload keys: {payload.keys()}")
    print(f"args keys: {payload['args'].keys()}")
    if 'messages' in payload['args'].keys():
        print(f"message keys: {payload['args']['messages'][0].keys()}")
        msg = payload['args']['messages'][0]
        if msg['mime_type'] == 'image/jpeg':
            print(f"Type of content is {type(msg['content'])}")
 
    # print(f"Payload is {payload}")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    response = json.loads(response['Payload'].read().decode("utf-8"))
    # print(f"Got response {response}")
    # body = json.loads(response['body'])
    # # print(f"Response body {body}")
    return response


def invoke_service(method, url, user_creds, *, body={}):
    # print(f"Using user_creds {user_creds}")
    service_url = '/'.join(url.split('/')[2])
    auth = AWSRequestsAuth(aws_access_key=user_creds['AccessKeyId'],
        aws_secret_access_key=user_creds['SecretKey'],
        aws_token=user_creds['SessionToken'],
        aws_host=service_url,
        aws_region=os.getenv('AWS_REGION'),
        aws_service='execute-api'
    )
    # print(f"Got auth {dir(auth)}")
    # print(f"Got auth {auth.__dict__}")
    # print(f"about to {method} {url}")
    headers = {
        'User-Agent': 'MTFSRAD-utils-invoke_service',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': get_ssm_params('origin_frontend'),
    }

    # print(f"Invoking {method} on {url} with headers {headers} and creds {user_creds}")

    if method == 'GET':
        response = requests.get(
            url,
            headers=headers,
            auth=auth
        )
    
    elif method == 'POST':
        # print(f"and body {body}")
        response = requests.post(
            url,
            headers=headers,
            json=body,
            auth=auth
        )
    # print(f"Got response {response}")
    return response

# max_download_attempts = 3
# def s3_download(bucket, s3_key, attempts=0, *, s3_client=None):
#     global s3_client_singleton
#     if not s3_client:
#         if not s3_client_singleton:
#             s3_client_singleton = BotoClientProvider.get_client('s3')
#         s3_client = s3_client_singleton
    
#     if attempts >= max_download_attempts:
#         raise Exception(f"Failed to download {s3_key} after {max_download_attempts} attempts.")
#     try:
#         parts = s3_key.split('/')
#         collection_id = parts[-2]
#         filename = parts[-1]
#         local_path = self.get_tmp_path(collection_id, filename)
#         self.s3.download_file(bucket, s3_key, local_path)
#         return local_path
#     except:
#         s3_prefix = '/'.join(s3_key.split('/')[:-1])
#         s3_key = f"{s3_prefix}/{unquote_plus(filename)}"
#         if attempts + 1 < max_download_attempts:
#             # print(f"Retrying download of {s3_key} (attempt {attempts + 1})")
#             return download_s3_file(bucket, s3_key, attempts + 1)
#         else:
#             raise Exception(f"ERROR: Failed to download s3://{bucket}/{s3_key} in {max_download_attempts} attempts.")

def sanitize_response(body, *, dont_sanitize_fields=[]):
    # # print(f"Sanitize_response received body {body}")
    if isinstance(body, dict):
        keys = list(body.keys())
        for key in keys:
            if key in sanitize_attributes and \
                key not in dont_sanitize_fields:
                # # print(f"\nDeleting {key}\n")
                del body[key]
            else:
                if isinstance(body[key], dict):
                    result = sanitize_response(body[key])
                    body[key] = result
    # # print(f"sanitize_response returning {body}")
    return body

def set_ingestion_status(user_id, doc_id, etag, lines_processed, progress_status, origin):
    response = invoke_lambda(
        get_ssm_params('ingestion_status_provider_function_name'),
        {
            "operation": "create_ingestion_status",
            "origin": origin,
            "args": {
                "user_id": user_id,
                "doc_id": doc_id,
                "etag": etag,
                "lines_processed": lines_processed,
                "progress_status": progress_status,
                "origin": "system"
            }
        }
    )