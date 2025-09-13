#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class EmbeddingsProviderEvent:
    def __init__(self, 
        dimensions='',
        input_text='',
        model_id='',
        operation='',
        origin='',
        embedding_type='search_query'
    ):
        self.dimensions = dimensions
        self.input_text = input_text
        self.model_id = model_id
        self.operation = operation
        self.origin = origin
        self.embedding_type = embedding_type
        

    def from_lambda_event(self, event):
        # print(f"embeddings_provider evt received event {event}")
        self.operation = event['operation']
        self.args = event['args']
        self.operation = event['operation']
        self.origin = event['origin']
        if 'dimensions' in self.args:
            self.dimensions = self.args['dimensions']
        else:
            self.dimensions = 1024
        if 'input_text' in self.args:
            self.input_text = self.args['input_text']
        if 'model_id' in self.args:
            self.model_id = self.args['model_id']
        if 'embedding_type' in self.args:
            self.embedding_type = self.args['embedding_type']
        else:
            self.embedding_type = 'search_query'
        return self

    def __str__(self):
        return json.dumps({
            "dimensions": self.dimensions,
            "input_text": self.input_text,
            "model_id": self.model_id,
            "operation": self.operation,
            "origin": self.origin
        })
