#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class VectorStoreProviderEvent:
    def __init__(self, 
        collection_id='',
        doc_id='',
        documents=[],
        operation='',
        origin='',
        query='',
        search_recommendations={},
        top_k=''
    ):
        self.collection_id = collection_id
        self.doc_id = doc_id
        self.documents = documents
        self.operation = operation
        self.origin = origin
        self.query = query
        self.search_recommendations = search_recommendations
        self.top_k = top_k

    def from_lambda_event(self, event):
        self.operation = event['operation']
        self.args = event['args']
        self.origin = event['origin']
        if 'collection_id' in self.args:
            self.collection_id = self.args['collection_id']
        if 'doc_id' in self.args:
            self.doc_id = self.args['doc_id']
        if 'documents' in self.args:
            self.documents = self.args['documents']
            print(f"VectorStoreProviderEvent loaded self.documents {self.documents}")
        if 'query' in self.args:
            self.query = self.args['query']
        if 'search_recommendations' in self.args:
            self.search_recommendations = self.args['search_recommendations']
        if 'top_k' in self.args:
            self.top_k = self.args['top_k']
        return self

    def __str__(self):
        return json.dumps({
            "collection_id": self.collection_id,
            "doc_id": self.doc_id,
            "documents": self.documents,
            "operation": self.operation,
            "origin": self.origin,
            "query": self.query,
            "search_recommendations": self.search_recommendations,
            "top_k": self.top_k
        })