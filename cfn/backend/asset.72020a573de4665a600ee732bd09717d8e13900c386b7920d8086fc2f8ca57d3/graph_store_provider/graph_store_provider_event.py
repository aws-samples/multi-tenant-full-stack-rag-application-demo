#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class GraphStoreProviderEvent:
    def from_lambda_event(self, event):
        self.origin = event['origin']
        self.operation = event['operation']
        args = event['args']
        self.collection_id = args['collection_id']
        self.statement = args['statement']
        self.statement_type = args['statement_type']
        return self

    def __str__(self):
        return json.dumps({
            "collection_id": self.collection_id,
            "operation": self.operation,
            "origin": self.origin,
            "statement": self.statement,
            "statement_type": self.statement_type
        })