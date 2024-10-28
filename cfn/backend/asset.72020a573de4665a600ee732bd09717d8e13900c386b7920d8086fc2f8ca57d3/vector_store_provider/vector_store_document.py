#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class VectorStoreDocument:
    def __init__(self,
        doc_id: str,
        content: str,
        metadata: dict,
        vector: list=[], 
        meta_fields_to_context=[]
    ):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata
        self.vector = vector
        self.meta_fields_to_context = meta_fields_to_context

    @staticmethod
    def from_dict(record): 
        if 'meta_fields_to_context' not in record:
            record['meta_fields_to_context'] = []
        return VectorStoreDocument(
            record['id'],
            record['content'],
            '{}' if 'metadata' not in record else record['metadata'],
            record['vector'],
            record['meta_fields_to_context']
        )

    def to_dict(self):
        return {
            'id': self.doc_id,
            'content': self.content,
            'metadata': self.metadata,
            'vector': self.vector,
            'meta_fields_to_context': self.meta_fields_to_context
        }

    def to_str(self):
        content = ''
        for field in self.meta_fields_to_context:
            content += f"{field.upper()}: {self.metadata[field]} "
        content += f"CONTENT: {self.content}"
        return content
       
    def to_json(self):
        tmp = {
            'id': self.doc_id,
            'content': self.content,
            'metadata': self.metadata,
            'vector': self.vector,
            'meta_fields_to_context': self.meta_fields_to_context
        }
        return json.dumps(tmp)