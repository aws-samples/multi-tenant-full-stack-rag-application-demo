#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class InitializationHandlerEvent:
    def from_lambda_event(self, event):
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
                print(f"Set self.origin to {self.origin}")

        if 'body' in event:
            body = json.loads(event['body'])
            self.urls_to_init = body['urls_to_init']
        if not hasattr(self, 'origin'):
            self.origin = ''
        return self
    

