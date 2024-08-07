#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class SharingHandlerEvent:
    def from_lambda_event(self, event):
        self.account_id = event['requestContext']['accountId']
        [self.method, self.path] = event['routeKey'].split(' ')
        if 'authorizer' in event['requestContext']:
            self.user_email = event['requestContext']['authorizer']['jwt']['claims']['email']
        if 'headers' in event:
            if 'authorization' in event['headers']:
                self.auth_token = event['headers']['authorization'].split(' ', 1)[1]
                # user_id will be added later
                self.user_id = None
            if 'origin' in event['headers']:
                print(f"Setting sharing handler event origin to {event['headers']['origin']}")
                self.origin = event['headers']['origin']
        if 'pathParameters' in event:
            if 'user_prefix' in event['pathParameters']:
                self.user_prefix = event['pathParameters']['user_prefix']
            if 'limit' in event['pathParameters']:
                self.limit = event['pathParameters']['limit']
            if 'last_eval_key' in event['pathParameters']:
                last_eval_key = event['pathParameters']['last_eval_key'] 
                self.last_eval_key = last_eval_key if last_eval_key != '*NONE*' else ''
            if 'collection_id' in event['pathParameters']:
                self.collection_id = event['pathParameters']['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id
                }
            if 'email' in event['pathParameters']:
                self.shared_with_email = event['pathParameters']['email']
        if 'body' in event:
            self.body = json.loads(event['body'])
            print(f"Loaded SharingHandlerEvent.body {self.body}")
            if "share_with_email" in self.body:
                self.shared_with_email = self.body['share_with_email']
            if "collection_id" in self.body:
                self.collection_id = self.body['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id
                }
        
        return self
    
    def __dict__(self):
        result = {
            'account_id': self.account_id,
            'method': self.method,
            'path': self.path
        }
        if hasattr(self, 'auth_token'):
            result['auth_token'] = self.auth_token,
        if hasattr(self, 'origin'):
            result['origin'] = self.origin
        if hasattr(self, 'user_prefix'):
            result['user_prefix'] = self.user_prefix
        if hasattr(self, 'limit'):
            result['limit'] = self.limit
        if hasattr(self, 'last_eval_key'):
            result['last_eval_key'] = self.last_eval_key
        if hasattr(self, 'body'):
            result['body'] = self.body
        if hasattr(self, 'collection_id'):
            result['collection_id'] = self.collection_id
        if hasattr(self, 'user_email'):
            result['user_email'] = self.user_email
        if hasattr(self, 'user_id'):
            result['user_id'] = self.user_id
        return result
            