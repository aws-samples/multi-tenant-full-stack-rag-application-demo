#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class CognitoAuthProviderEvent:
    def __init__(self, 
        account_id='',
        auth_token='',
        method='',
        path='',
        user_email='',
        user_id='',
        origin=''
    ):
        self.account_id = account_id
        self.auth_token = auth_token
        self.method = method
        self.path = path,
        self.user_email = user_email
        self.user_id = user_id
        self.origin = origin
        

    def from_lambda_event(self, event):
        print(f"cognito auth provider evt received event {event}")
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
                
        return self
