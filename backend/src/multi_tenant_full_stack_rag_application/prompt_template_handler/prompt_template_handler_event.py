#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import uuid


class PromptTemplateHandlerEvent:
    def __init__(self,
        account_id='',
        auth_token='',
        template_id='',
        template_text='',
        method='',
        path='',
        user_email='',
        user_id='',
        origin=''
    ):
        self.account_id = account_id
        self.auth_token = auth_token
        self.template_id = template_id if template_id != '' else uuid.uuid4()
        self.template_text = template_text
        self.method = method
        self.path = path
        self.user_email = user_email
        self.user_id = user_id
        self.origin = origin

    def from_lambda_event(self, event):
        self.account_id = event['requestContext']['accountId']
        [self.method, self.path] = event['routeKey'].split(' ')
        if 'authorizer' in event['requestContext']:
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

            template = body['prompt_template']
            if 'template_name' in template:
                self.template_name = template['template_name']
            if 'template_text' in template:
                self.template_text = template['template_text']
            if 'model_ids' in template:
                self.model_ids = template['model_ids']
            if 'template_id' in template:
                self.template_id = template['template_id']
            if 'stop_sequences' in template:
                self.stop_sequences = template['stop_sequences']    
        if 'pathParameters' in event:
            self.path_parameters = event['pathParameters']
            if 'template_id' in self.path_parameters:
                self.template_id = self.path_parameters['template_id']
        # print(f'from_lambda_event returning {self.__dict__}')      
        return self

    def __str__(self):
        args = {
            "account_id": self.account_id,
            "method": self.method,
            "path": self.path,
            "template_id": self.template_id,
            "template_text": self.template_text,
            "user_email": self.user_email,
            "user_id": self.user_id,
        }
        if hasattr(self, 'auth_token'): 
            args['auth_token'] = self.auth_token
        if hasattr(self, 'model_ids'):
            args['model_ids'] = self.model_ids
        if hasattr(self, 'stop_sequences'):
            args['stop_sequences'] = self.stop_sequences
        if hasattr(self, 'origin'):
            args['origin'] = self.origin
        return json.dumps(args)
