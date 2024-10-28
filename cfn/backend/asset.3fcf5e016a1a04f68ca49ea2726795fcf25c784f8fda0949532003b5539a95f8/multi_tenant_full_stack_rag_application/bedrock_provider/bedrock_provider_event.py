#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class BedrockProviderEvent:
    def __init__(self,
        chunk_text='',
        dimensions=0,
        input_type='',
        messages=[],
        model_id='',
        model_kwargs={},
        operation='',
        origin='',
        prompt='',
        search_text='',
        input_text='',
    ):
        # now assign all variables to self.
        self.chunk_text = chunk_text
        self.dimensions = dimensions
        self.input_type = input_type
        self.messages = messages
        self.model_id = model_id
        self.model_kwargs = model_kwargs
        self.operation = operation
        self.origin = origin
        self.prompt = prompt
        self.search_text = search_text
        self.input_text = input_text

    def from_lambda_event(self, event):
        self.operation = event['operation']
        self.origin = event['origin']
        args = event['args']
        self.model_id = args['model_id']
        
        # assign the args without defaults or 
        # that only exist on one operation
        # like this, so you'll get an error
        # on that operation if they're not there.
        if self.operation == 'embed_text':
            self.input_text = args['input_text']
        
        elif self.operation == 'get_semantic_similarity':
            self.chunk_text = args['chunk_text']
            self.search_text= args['search_text']
        
        elif self.operation == 'invoke_model':
            if 'model_kwargs' in args:
                self.model_kwargs = args['model_kwargs']
            if 'messages' in args:
                self.messages = args['messages']
            elif 'prompt' in args:
                self.prompt = args['prompt']
            else:
                raise Exception("invoke_model requires either 'prompt' or 'messages'")
        
        # now do the ones with defaults like this:        
        if 'dimensions' in args:
            self.dimensions = args['dimensions']
        if 'input_type' in args:
            self.input_type = args['input_type']

        return self

    def __str__(self):
        return json.dumps({
            "method": self.method,
            "operation": self.operation,
            "params": self.params,
            "body": self.body 
        })