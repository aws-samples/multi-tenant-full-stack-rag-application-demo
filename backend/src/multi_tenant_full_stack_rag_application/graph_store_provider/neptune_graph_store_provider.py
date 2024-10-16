#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
import json
from .graph_store_provider import GraphStoreProvider
from .graph_store_provider_event import GraphStoreProviderEvent
import multi_tenant_full_stack_rag_application.graph_store_provider.neptune_client as neptune
from multi_tenant_full_stack_rag_application import utils

# API
# evt = {
#   "operation": [exec_stmt],
#   "origin": origin string of caller,
#   "args":
#       exec_stmt: {
#           "collection_id": str,
#           "statement_type": str,
#           "statement": str,
# }

graph_store_provider = None


class NeptuneGraphStoreProvider(GraphStoreProvider):
    def __init__(self, neptune_client, neptune_endpoint):
        self.utils = utils
        self.neptune = neptune_client
        self.neptune_endpoint = neptune_endpoint
        self.allowed_origins = self.utils.get_allowed_origins()
        print(f"NeptuneGraphStoreProvider initialized with allowed_origins {self.allowed_origins}")

    def execute_statement(self, collection_id, statement, statement_type='gremlin'):
        print(f"Running neptune statement {statement}")
        neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', statement_type, statement)
        print(f"Got neptune response {neptune_response}")
        if isinstance(neptune_response, str):
            neptune_response = json.loads(neptune_response)
        if 'status' in neptune_response and \
        'code' in neptune_response['status'] and \
        neptune_response['status']['code'] == 200:
            return neptune_response
        else:
            print(f"Error processing gremlin statement {statement}")
            return False

    def handler(self, event):
        handler_evt = GraphStoreProviderEvent().from_lambda_event(event)
        status = 200
        result = {}
        if handler_evt.origin not in self.allowed_origins.values() or \
            handler_evt.origin == self.allowed_origins['origin_frontend']:
            return self.utils.format_response(403, {"error": "forbidden"}, handler_evt.origin)
        elif handler_evt.operation == 'execute_statement':
            result = {
                "response": self.execute_statement(
                    handler_evt.collection_id,
                    handler_evt.statement,
                    handler_evt.statement_type
                )   
            }             
        return self.utils.format_response(status, result, handler_evt.origin)

def handler(event, context):
    global graph_store_provider
    if not graph_store_provider:
        neptune_client = neptune
        graph_provider_endpoint = utils.get_ssm_params('neptune_endpoint_address')
        graph_store_provider = NeptuneGraphStoreProvider(neptune_client, graph_provider_endpoint)
    result = graph_store_provider.handler(event)
    print(f"neptune_graph_store_provider returning {result}")
    return result