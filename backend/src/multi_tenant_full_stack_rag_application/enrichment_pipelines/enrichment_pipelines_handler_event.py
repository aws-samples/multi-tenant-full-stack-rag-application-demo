#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class EnrichmentPipelinesHandlerEvent:

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
        # if 'body' in event:
        #     body = json.loads(event['body'])
        #     if 'document_collection' in body:
        #         self.document_collection=body['document_collection']
        #     elif 'collection_id' in body:
        #         self.collection_id = body['collection_id']
        #         self.document_collection = {
        #             "collection_id": self.collection_id
        #         }
        # if 'pathParameters' in event:
        #     self.path_parameters = event['pathParameters']
        #     if 'collection_id' in self.path_parameters:
        #         self.collection_id = self.path_parameters['collection_id']
        #         self.document_collection = {
        #             "collection_id": self.collection_id
        #         }
        return self
