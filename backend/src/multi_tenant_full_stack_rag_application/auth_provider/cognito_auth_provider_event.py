#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class CognitoAuthProviderEvent:
    def __init__(self, 
        auth_token='',
        operation='',
        origin='',
        user_id=''
    ):
        self.auth_token = auth_token
        self.operation = operation
        self.origin = origin
        self.user_id = user_id
        

    def from_lambda_event(self, event):
        # # print(f"cognito auth provider evt received event {event}")
        self.operation = event['operation']
        self.origin = event['origin']
        if 'auth_token' in event['args']:
            self.auth_token = event['args']['auth_token']
        if 'user_id' in event:
            self.user_id = event['args']['user_id']

        return self
