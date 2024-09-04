#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class DocumentCollectionsHandlerEvent:
    def __init__(self, 
        account_id='',
        collection_id='', 
        method='',
        path='',
        user_email='',
        user_id='',
        origin=''
    ):
        print(f"dch evt received user_id '{user_id}' (may be uninitialized and populated later)")
        self.account_id = account_id
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
            if 'document_collection' in body:
                self.document_collection=body['document_collection']
                if 'enrichment_pipelines' in body:
                    self.enrichment_pipelines = json.dumps(body['document_collection']['enrichment_pipelines'])
                else:
                    self.enrichment_pipelines = {}
                    
            elif 'collection_id' in body:
                self.collection_id = body['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id,
                }
                if 'collection_name' in body:
                    self.collection_name = body['collection_name']
                    self.document_collection['collection_name'] = self.collection_name
                
        if 'pathParameters' in event:
            self.path_parameters = event['pathParameters']
            if 'collection_id' in self.path_parameters:
                self.collection_id = self.path_parameters['collection_id']
                self.document_collection = {
                    "collection_id": self.collection_id
                }
        return self
