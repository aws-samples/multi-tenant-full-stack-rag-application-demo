#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class GenerationHandlerEvent:
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
        if 'body' in event:
            self.message_obj = json.loads(event['body'])['messageObj']
        return self

    def __dict__(self):
        dict_val = {
            "method": self.method,
            "path": self.path,
        }
        if hasattr(self, 'auth_token'):
            dict_val['auth_token'] = self.auth_token
        if hasattr(self, 'origin'):
            dict_val['origin'] = self.origin
        if hasattr(self, 'message_obj'):
            dict_val['message_obj'] = self.message_obj
        return dict_val
