from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument


class MockVectorStoreProvider(VectorStoreProvider):
    
    def create_index(self, collection_id):
        return collection_id

    def delete_index(self, collection_id):
        return collection_id

    def delete_record(self, collection_id, record_id):
        return True
    
    def get_vector_store(self, collection_id):
        pass

    def query(self, collection_id, query):
        return { "collection_id": collection_id, "query": query}
    
    def semantic_query(self, search_recommendations, top_k=5, score_threshold=0.2):
        return { "collection_id": collection_id, "query": query}
    
    def save(self, doc_chunks, collection_id, *, return_docs=False, return_vectors=False):
        return len(doc_chunks)