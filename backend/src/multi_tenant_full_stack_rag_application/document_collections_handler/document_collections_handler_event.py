#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class DocumentCollectionsHandlerEvent:
    def __init__(self, 
        account_id='',
        auth_token='',
        collection_id='', 
        method='',
        path='',
        user_email='',
        user_id='',
        origin=''
    ):
        print(f"dch evt received user_id '{user_id}' (may be uninitialized and populated later)")
        self.account_id = account_id
        self.auth_token = auth_token
        self.collection_id = collection_id
        self.method = method
        self.path = path,
        self.user_email = user_email
        self.user_id = user_id
        self.origin = origin

    def from_lambda_event(self, event):
        print(f"dch evt.from_lambda_event received event {event}")
        self.account_id = event['requestContext']['accountId']
        [self.method, self.path] = event['routeKey'].split(' ')
        if 'authorizer' in event['requestContext'] and \
            'jwt' in event['requestContext']['authorizer'] and \
            'claims' in event['requestContext']['authorizer']['jwt'] and \
            'email' in event['requestContext']['authorizer']['jwt']['claims']:
            self.user_email = event['requestContext']['authorizer']['jwt']['claims']['email']
        if 'headers' in event:
            if 'authorization' in event['headers']:
                self.auth_token = event['headers']['authorization'].split(' ', 1)[1]
            if 'origin' in event['headers']:
                self.origin = event['headers']['origin']
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']

            if 'document_collection' in body:
                self.document_collection=body['document_collection']
                    
            elif 'collection_id' in body:
                self.collection_id = body['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id,
                }
                if 'collection_name' in body:
                    self.collection_name = body['collection_name']
                    self.document_collection['collection_name'] = self.collection_name
                if 'user_id' in body:
                    self.document_collection['user_id'] = body['user_id']
                    self.user_id = body['user_id']
                elif 'user_email' in body:
                    self.document_collection['user_email'] = body['user_email']
                    self.user_email = body['user_email']
            
            if not hasattr(self, 'user_id') and \
                'user_id' in event:
                    self.document_collection['user_id'] = event['user_id']
                    self.user_id = event['user_id']
            if  not hasattr(self, 'user_email') and \
                'user_email' in event:
                    self.document_collection['user_email'] = event['user_email']
                    self.user_email = event['user_email']

        if 'pathParameters' in event:
            self.path_parameters = event['pathParameters']
            if 'collection_id' in self.path_parameters:
                self.collection_id = self.path_parameters['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id
                }
            if 'file_id' in self.path_parameters:
                self.file_id = self.path_parameters['file_id']
            if 'last_eval_key' in self.path_parameters:
                self.last_eval_key = self.path_parameters['last_eval_key']
            if 'limit' in self.path_parameters:
                self.limit = self.path_parameters['limit']
                

        if hasattr(self, 'document_collection') and \
            'user_email' in self.document_collection and \
            not hasattr(self, 'user_email'):
            self.user_email = self.document_collection['user_email']

        return self
