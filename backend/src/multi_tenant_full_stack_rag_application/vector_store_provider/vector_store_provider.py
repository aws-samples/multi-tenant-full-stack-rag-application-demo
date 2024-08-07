#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod

from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument

class VectorStoreProvider(ABC):
    def __init__(self, 
        embeddings_provider: EmbeddingsProvider,
        vector_store_endpoint: str,
        **args
    ): 
        self.embeddings_provider = embeddings_provider
        self.vector_store_endpoint = vector_store_endpoint

    @abstractmethod
    def create_index(self, collection_id):
        pass

    @abstractmethod
    def delete_index(self, collection_id):
        pass

    @abstractmethod
    def delete_record(self, collection_id, id):
        pass

    @abstractmethod
    def query(self, collection_id, query):
        pass

    @abstractmethod
    def semantic_query(self, search_recommendations, top_k: int=5, score_threshold: float=0.2) -> [VectorStoreDocument]:
        pass        

    @abstractmethod
    def save(self, docs: [VectorStoreDocument], collection_id): 
        pass