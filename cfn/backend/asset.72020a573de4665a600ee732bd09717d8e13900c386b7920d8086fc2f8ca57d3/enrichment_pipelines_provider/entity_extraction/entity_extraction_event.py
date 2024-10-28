#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class EntityExtractionProviderEvent:
    def from_lambda_event(self, event):
        files_to_process = []
        for record in event['Records']:
            new_image = record['dynamodb']['NewImage']
            doc_id = new_image['doc_id']['S']
            parts = doc_id.split('/')
            collection_id = parts[0]
            filename = '/'.join(parts[1:])
            files_to_process.append({
                "collection_id": collection_id,
                "filename": filename
            })
        self.files_to_process = files_to_process
        return self

    def __str__(self):
        return json.dumps({
            "dimensions": self.dimensions,
            "input_text": self.input_text,
            "model_id": self.model_id,
            "operation": self.operation,
            "origin": self.origin
        })