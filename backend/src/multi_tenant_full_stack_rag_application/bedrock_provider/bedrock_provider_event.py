#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class BedrockProviderEvent:
    def __init__(self, 
        account_id='',
        auth_token='',
        method='',
        path='',
        origin=''
    ):
        self.account_id = account_id
        self.auth_token = auth_token
        self.method = method
        self.path = path
        self.origin = origin
        

    def from_lambda_event(self, event):
        print(f"bedrock_provider evt received event {event}")
        self.account_id = event['requestContext']['accountId']
        [self.method, self.path] = event['routeKey'].split(' ')
        if 'authorizer' in event['requestContext']:
            self.user_email = event['requestContext']['authorizer']['jwt']['claims']['email']
        if 'headers' in event:
            if 'authorization' in event['headers']:
                self.auth_token = event['headers']['authorization'].split(' ', 1)[1]
                # user_id will be inserted later
                self.user_id = None
            if 'origin' in event['headers']:
                self.origin = event['headers']['origin']
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
            self.operation = body['operation']
            self.body = body['args']

        if 'pathParameters' in event:
            self.path_parameters = event['pathParameters']
                
        return self

    def __str__(self):
        return json.dumps({
            "method": self.method,
            "operation": self.operation,
            "params": self.params,
            "body": self.body 
        })