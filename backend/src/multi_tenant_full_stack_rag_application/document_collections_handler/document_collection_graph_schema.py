#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import time
from datetime import datetime


class DocumentCollectionGraphSchema:
    def __init__(self,
        user_id: str,
        collection_name: str,
        graph_schema: dict,
        timestamp_ms: int = None
    ):
        self.user_id = user_id
        self.collection_name = collection_name
        self.graph_schema = graph_schema if isinstance(graph_schema, dict) else json.loads(graph_schema)
        self.timestamp_ms = timestamp_ms if timestamp_ms else int(time.time() * 1000)
        self.sort_key = f"graph_schema::{collection_name}::{self.timestamp_ms}"
        now = datetime.now().isoformat() + 'Z'

    @staticmethod
    def from_ddb_record(rec):
        """Create DocumentCollectionGraphSchema from DynamoDB record"""
        # Extract timestamp from sort key
        sort_key_parts = rec['sort_key']['S'].split('::')
        timestamp_ms = int(sort_key_parts[-1])
        
        return DocumentCollectionGraphSchema(
            rec['partition_key']['S'],
            rec['collection_name']['S'],
            json.loads(rec['graph_schema']['S']),
            timestamp_ms
        )

    def to_ddb_record(self):
        """Convert to DynamoDB record format"""
        return {
            'partition_key': {'S': self.user_id},
            'sort_key': {'S': self.sort_key},
            'collection_name': {'S': self.collection_name},
            'graph_schema': {'S': json.dumps(self.graph_schema if self.graph_schema else {})},
            'timestamp_ms': {'N': str(self.timestamp_ms)}
        }

    def __dict__(self):
        return {
            'user_id': self.user_id,
            'collection_name': self.collection_name,
            'sort_key': self.sort_key,
            'graph_schema': json.dumps(self.graph_schema),
            'timestamp_ms': self.timestamp_ms
        }

    def __str__(self):
        return json.dumps(self.__dict__())

    def __eq__(self, obj):
        return (
            self.user_id == obj.user_id and
            self.collection_name == obj.collection_name and
            self.graph_schema == obj.graph_schema and
            self.timestamp_ms == obj.timestamp_ms
        )
