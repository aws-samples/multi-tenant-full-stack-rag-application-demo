#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class PromptTemplateHandlerEvent:
    def from_lambda_event(self, event):
        [self.method, self.path] = event['routeKey'].split(' ')
        if 'headers' in event:
            if 'authorization' in event['headers']:
                self.auth_token = event['headers']['authorization'].split(' ', 1)[1]
            if 'origin' in event['headers']:
                self.origin = event['headers']['origin']
        if 'body' in event:
            template = json.loads(event['body'])['prompt_template']
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

        return self

    def __str__(self):
        args = {
            "method": self.method,
            "path": self.path,
        }
        if hasattr(self, 'auth_token'): 
            args['auth_token'] = self.auth_token
        if hasattr(self, 'origin'):
            args['origin'] = self.origin
        if hasattr(self, 'prompt_template'):
            args['prompt_template'] = self.prompt_template
        if hasattr(self, 'model_ids'):
            args['model_ids'] = self.model_ids
        if hasattr(self, 'stop_sequences'):
            args['stop_sequences'] = self.stop_sequences
        return json.dumps(args)
