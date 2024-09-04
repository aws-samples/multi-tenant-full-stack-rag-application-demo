#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth


from .boto_client_provider import BotoClientProvider

sanitize_attributes = ['user_id', 'shared_by_userid', 'shared_with_userid']

cognito_identity_client = None
cognito_identity_id_singleton = None
cognito_user_pool_id_singleton = None
lambda_client_singleton = None
s3_client_singleton = None
sqs_client_singleton = None
ssm_client_singleton = None
ssm_params = None

# def delete_sqs_message(rcpt_handle:str, queue_url: str, *, sqs_client=None): 
#     if not sqs_client:
#         if not sqs_client_singleton:
#             sqs_client_singleton = BotoClientProvider.get_client('sqs')
    
#     sqs_client = sqs_client_singleton
    
#     try: 
#         sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=rcpt_handle)
#     except Exception as e:
#         print(f"e.args[0] == {e.args[0]}")
#         if "NonExistentQueue" in e.args[0]:
#             print("CAUGHT ERROR due to non-existent queue in dev")
#         elif "ReceiptHandleIsInvalid" in e.args[0]:
#             print("CAUGHT ERROR due to non-existent receipt handle in dev.")            
#         else:
#             raise Exception(f'Error occurred while deleting message: {e.args[0]}')

def format_response(status, body, origin):
    body = sanitize_response(body)
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
    print(f"Returning response {response}")
    return response 

def get_cognito_identity_client():
    global cognito_identity_client
    if not cognito_identity_client:
        cognito_identity_client = BotoClientProvider.get_client('cognito-identity')
    return cognito_identity_client
    
def get_identity_pool_id():
    global cognito_identity_id_singleton
    if not cognito_identity_id_singleton:
        cognito_identity_id_singleton = get_ssm_params('identity_pool_id')
    return cognito_identity_id_singleton

def get_ssm_client():
    global ssm_client_singleton
    if not ssm_client_singleton:
        ssm_client_singleton = BotoClientProvider.get_client('ssm')
    return ssm_client_singleton

# use without a param to get all params in the 
# stack
def get_ssm_params(param=''):
    global ssm_params
    ssm_client = get_ssm_client()
    if not ssm_params:  
        ssm_params = {}  
        response = ssm_client.get_parameters_by_path(
            Path=f'/{os.getenv("STACK_NAME")}/{param}',
            Recursive=True
        )['Parameters']
        for param in response:
            ssm_params[param['Name'].split('/')[-1]] = param['Value']
    if param:
        print(f"Params are {ssm_params}")
        return ssm_params[param]
    else:
        return ssm_params

def get_user_pool_id():
    global cognito_user_pool_id_singleton
    if not cognito_user_pool_id_singleton:
        cognito_user_pool_id_singleton = get_ssm_params('user_pool_id')
        # ssm_client = BotoClientProvider.get_client('ssm')
        # response = ssm_client.get_parameter(
        #     Name=f'/{os.getenv("STACK_NAME")}/user_pool_id'
        # )
        # cognito_user_pool_id_singleton = response['Parameter']['Value']
    return cognito_user_pool_id_singleton

def invoke_lambda(function_name, payload, *, lambda_client=None):
    global lambda_client_singleton
    if not lambda_client:
        if not lambda_client_singleton:
            lambda_client = BotoClientProvider.get_client('lambda')
        else:
            lambda_client = lambda_client_singleton
    response = lambda_client_singleton.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    return response


def invoke_service(service_name, payload, jwt):
    identity_pool_id = get_identity_pool_id()
    user_pool_id = get_user_pool_id()
    cognito_identity_client = get_cognito_identity_client()
    user_id = cognito_identity_client.get_userid_from_token(jwt)
    creds = cognito_identity_client.get_credentials_for_identity(
        IdentityPoolId=identity_pool_id,
        Logins={
            f'cognito-idp.{os.getenv("AWS_REGION")}.amazonaws.com/{user_pool_id}': jwt
        }
    )
    print(f"Got creds {creds}")

    # auth = AWSRequestsAuth(aws_access_key=creds.aws_access_key,
    #     aws_secret_access_key=creds.aws_secret_access_key,
    #     aws_session_token=creds.aws_session_token,
    #     aws_host='restapiid.execute-api.us-east-1.amazonaws.com',
    #     aws_region='us-east-1',
    #     aws_service='execute-api'
    # )

    # headers = {'params': 'ABC'}
    # response = requests.get(
    #     'https://restapiid.execute-api.us-east-1.amazonaws.com/stage/resource_path',
    #     auth=auth, 
    #     headers=headers
    # )

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
#             print(f"Retrying download of {s3_key} (attempt {attempts + 1})")
#             return download_s3_file(bucket, s3_key, attempts + 1)
#         else:
#             raise Exception(f"ERROR: Failed to download s3://{bucket}/{s3_key} in {max_download_attempts} attempts.")


def sanitize_response(body):
    # print(f"Sanitize_response received body {body}")
    if isinstance(body, dict):
        keys = list(body.keys())
        for key in keys:
            if key in sanitize_attributes:
                # print(f"\nDeleting {key}\n")
                del body[key]
            else:
                if isinstance(body[key], dict):
                    result = sanitize_response(body[key])
                    body[key] = result
    # print(f"sanitize_response returning {body}")
    return body

