#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from boto3.session import Session
from opensearchpy import  OpenSearch, RequestsHttpConnection
from queue import Queue
from requests_aws4auth import AWS4Auth
from threading import Thread

from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_event import VectorStoreProviderEvent
from multi_tenant_full_stack_rag_application import utils


# API
#    operation: [ create_index | delete_index | delete_record | query | save | semantic_query | ]
#    args:
#       for create_index: collection_id
#       for delete_index: collection_id
#       for delete_record: collection_id, doc_id
#       for query: collection_id, query, top_k
#       for save: collection_id, document
#       for semantic_query: search_recommendations (mapping of collection IDs to keywords to search for in those collections), 
#                           top_k


vector_store_provider = None


class OpenSearchVectorStoreProvider(VectorStoreProvider):
    def __init__(self, 
        vector_store_endpoint: str,
        port=443,
        proto='https',
        **kwargs
    ):         
        super().__init__(vector_store_endpoint)
        self.utils = utils
        self.vector_store_endpoint = vector_store_endpoint
        self.port = port
        self.proto = proto
        # self.user = user
        # self.pwd = pwd
        self.allowed_origins = self.utils.get_allowed_origins()
        self.my_origin = self.utils.get_ssm_params('origin_vector_store_provider')
    
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
                        "dimension": self.utils.get_model_dimensions(self.my_origin)
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
    
    def handler(self, event, context):
        print(f'OpenSearchVectorStoreProvider got event {event}')
        handler_evt = VectorStoreProviderEvent().from_lambda_event(event)
        
        status = 200
        result = {}

        if handler_evt.origin not in self.allowed_origins.values():
            print(f"handler_evt.origin {handler_evt.origin} is not in allowed origins {self.allowed_origins}")
            status = 403
            result = {"error": "Access denied"}
            
        elif handler_evt.operation == 'create_index':
            result = self.create_index(handler_evt.collection_id)
    
        elif handler_evt.operation == 'delete_index':
            result = self.delete_index(handler_evt.collection_id)
        
        elif handler_evt.operation == 'delete_record':
            result = self.delete_record(handler_evt.collection_id, handler_evt.doc_id)

        elif handler_evt.operation == 'query':
            result = self.query(handler_evt.collection_id, handler_evt.query)

        elif handler_evt.operation == 'save':
            result = self.save(handler_evt.documents, handler_evt.collection_id)

        elif handler_evt.operation == 'semantic_query':
            result = self.semantic_query(handler_evt.search_recommendations, handler_evt.top_k)

        else:
            status = 400
            result = {'error', 'Unknown operation'}

        return self.utils.format_response(status, result, self.my_origin)
    
    def query(self, collection_id, query):
        os_vector_db = self.get_vector_store(collection_id)
        return os_vector_db.search(
            body=query,
            index=collection_id
        )
        
    def save(self, doc_chunks: [VectorStoreDocument], collection_id, *, return_docs=False, return_vectors=False): 
        os_vector_db = self.get_vector_store(collection_id)
        payload = ''
        print(f"Saving {len(doc_chunks)} (type {type(doc_chunks[0])}) documents to vector store {collection_id}")
        doc_ids = []
        for doc in doc_chunks:
            print(f"saving doc {doc}")
            doc_id = doc['id']
            doc_ids.append(doc_id)
            if doc_id.startswith(f"{collection_id}/"):
                doc_id = doc_id.replace(f"{collection_id}/", "")
            # print(f"ingesting document {doc}")
            if 'id' in list(doc.keys()):
                del doc['id']
            # delattr(doc, 'id')
            doc['vector'] = self.utils.embed_text(doc['content'], self.my_origin)
            payload += '{"index": { "_index": "' + collection_id + '", "_id": "' + doc_id + '"}}\n' + json.dumps(doc) + "\n"
        
        print(f"Saving payload {payload}")
        result = os_vector_db.bulk(payload, params={
            'refresh': 'true'
        })

        if result['errors']:
            raise Exception(f"Error saving to vector store: {result}")
            
        print(f"Result from saving doc to vector store: {result}")
        return doc_ids

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
                vector = self.utils.embed_text(search_query, self.my_origin)
        
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


def handler(event, context):
    global vector_store_provider
    if not vector_store_provider:
        print(f'vector_store_provider.handler got event {event}')
        vs_endpoint = os.getenv('VECTOR_STORE_ENDPOINT')
        vector_store_provider = OpenSearchVectorStoreProvider(vs_endpoint)
    return vector_store_provider.handler(event, context)

    
