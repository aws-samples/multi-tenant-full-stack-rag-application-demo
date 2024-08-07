#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.graph_store_provider import GraphStoreProvider

class NeptuneGraphStoreProvider(GraphStoreProvider):
    
    def execute_query(self, collection_id):
        pass