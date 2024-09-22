#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from boto3.session import Session
from opensearchpy import  OpenSearch, RequestsHttpConnection
from queue import Queue
from requests_aws4auth import AWS4Auth
from threading import Thread

from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider

# API
# DELETE /vector_store/{operation}/{resource_id}
#            .../index/index_id
#.           .../record/record_id
# POST /vector_store/{operation}
#        .../create_index
#        .../query
#.       .../save
#        .../semantic_query


class OpenSearchVectorStoreProvider(VectorStoreProvider):
    def __init__(self, 
        vector_store_endpoint: str,
        port=443,
        proto='https',
        **kwargs
    ):         
        super().__init__(vector_store_endpoint)
        self.vector_store_endpoint = vector_store_endpoint
        self.port = port
        self.proto = proto
        # self.user = user
        # self.pwd = pwd

    def create_index(self, collection_id):
        os_vector_db = self.get_vector_store(collection_id)
        index_body = {
            "settings": {
                "index.knn": True
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "vector": {
                        "type": "knn_vector",
                        "dimension": self.embeddings.get_model_dimensions()
                    },
                    "metadata": {"type": "object"}
                }
            }
        }
        try: 
            if not os_vector_db.indices.exists(collection_id):
                os_vector_db.indices.create(
                    index=collection_id, 
                    body=index_body
                )
        except Exception:
            pass

        return collection_id

    def delete_index(self, collection_id):
        os_vector_db = self.get_vector_store(collection_id)
        return os_vector_db.indices.delete(
            index = collection_id
        )

    def delete_record(self, collection_id, doc_id):
        os_vector_db = self.get_vector_store(collection_id)
        return os_vector_db.delete(
            index=collection_id,
            id=doc_id
        )
        
    def get_vector_store(self, collection_id):
        if not hasattr(self, 'vector_db_client') or not self.vector_db_client:
            service = 'es'
            kwargs = {
                "is_aoss": False,
                "connection_class": RequestsHttpConnection,
                "http_compress": True, # enables gzip compression for request bodies
                "engine": "hnsw"
            }
            sess = boto3.session.Session()
            region = sess.region_name
            if self.vector_store_endpoint != 'localhost':
                creds = sess.get_credentials()
                awsauth = AWS4Auth(creds.access_key, creds.secret_key, region, service, session_token=creds.token)
                kwargs["http_auth"] = awsauth
            # this is only to support testing. It doesn't impact prod.
            # else:
            #     kwargs["http_auth"] = (self.user, self.pwd)

            kwargs["use_ssl"] = True if self.proto == 'https' else False
            kwargs["verify_certs"] = False if self.vector_store_endpoint == 'localhost' else True
            self.vector_db_client = OpenSearch(
                f"{self.proto}://{self.vector_store_endpoint}:{self.port}",
                **kwargs
            )
            if not self.vector_db_client.indices.exists(collection_id):
                self.create_index(collection_id)
    
        return self.vector_db_client
    
    def query(self, collection_id, query):
        os_vector_db = self.get_vector_store(collection_id)
        return os_vector_db.search(
            body=query,
            index=collection_id
        )
        
    def semantic_query(self, search_recommendations, top_k: int=5, score_threshold: float=0.2) -> [VectorStoreDocument]:
        in_queue = Queue()
        out_queue = Queue()
        
        if not isinstance(search_recommendations, list):
            search_recommendations = [search_recommendations]

        for recommendation in search_recommendations:
            in_queue.put(recommendation)

        q_len = in_queue.qsize() - 1

        def consumer(in_queue, out_queue, top_k):
            recommendation = in_queue.get()
            while recommendation:
                id = recommendation['id']
                search_query = recommendation['vector_database_search_terms']
                results = {}
                vector = self.embeddings.embed_text(search_query)
        
                search_query = { 
                    "size": top_k,
                    "query": { 
                        "knn": {     
                            "vector": {
                                "vector": vector,
                                "k": top_k 
                            }
                        }
                    }
                }
                next_token = None
                os_vector_db = self.get_vector_store(id) 
                response = os_vector_db.search(
                    body=search_query,
                    index=id
                )
                docs = []
                if 'hits' in response:
                    max_score = 0
                    if 'max_score' in response['hits']:
                        max_score = response['hits']['max_score']
                    if 'hits' in response['hits']:
                        docs = response['hits']['hits']
                max_score = response['hits']['max_score']
                for doc in docs:
                    score = doc['_score'] / max_score # normalize
                    new_doc = doc['_source']
                    new_doc['metadata']['score'] = score
                    new_doc['id'] = doc['_id']
                    out_queue.put(new_doc)
                in_queue.task_done()
                recommendation = in_queue.get()
        
        consumer = Thread(target=consumer, args=(in_queue, out_queue, top_k), daemon=True)
        consumer.start()
        in_queue.join()
    
        final_docs = []

        for i in range(out_queue.qsize()):
            doc = out_queue.get()
            final_docs.append(doc)
        
        return final_docs

    def save(self, doc_chunks: [VectorStoreDocument], collection_id, *, return_docs=False, return_vectors=False): 
        os_vector_db = self.get_vector_store(collection_id)
        payload = ''
        for doc in doc_chunks:
            doc = doc.to_dict()
            doc_id = doc['id']
            if doc_id.startswith(f"{collection_id}/"):
                doc_id = doc_id.replace(f"{collection_id}/", "")
            # print(f"ingesting document {doc}")
            if 'id' in list(doc.keys()):
                del doc['id']
            # delattr(doc, 'id')
            doc['vector'] = self.embeddings.embed_text(doc['content'])
            payload += '{"index": { "_index": "' + collection_id + '", "_id": "' + doc_id + '"}}\n' + json.dumps(doc) + "\n"
        
        result = os_vector_db.bulk(payload, params={
            
            'refresh': 'true'
        })
        # print(f"Result from saving doc to vector store: {result}")
        return len(doc_chunks)

