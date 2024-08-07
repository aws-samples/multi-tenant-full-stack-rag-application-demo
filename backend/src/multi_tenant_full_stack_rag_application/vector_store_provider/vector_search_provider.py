#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollectionsHandler
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSettingsProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider


class VectorSearchProvider:
    def __init__(self, 
        document_collections_handler: DocumentCollectionsHandler,
        user_settings_provider: UserSettingsProvider,
        vector_store_provider: VectorStoreProvider
    ):
        self.document_collections_handler = document_collections_handler
        self.user_settings_provider = user_settings_provider
        self.vector_store_provider = vector_store_provider
        # self.query = self.vector_store_provider.query
        self.model_max_length = self.vector_store_provider.embeddings_provider.get_model_max_tokens()
        self.get_token_ct = self.vector_store_provider.embeddings_provider.get_token_count
        self.embeddings_provider = self.vector_store_provider.embeddings_provider

    def compress_results(self, docs, query):
        compression_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.model_max_length,
            chunk_overlap=floor(self.model_max_length * 0.05),
            length_function=self.get_token_ct
        )

        docs_split = compression_splitter.transform_documents(docs)
        compressed_docs = self.embeddings_filter.compress_documents(
            docs_split,
            query
        )
        return compressed_docs

    def get_parent_docs(self, docs):
        tmp_docs = {}
        for doc in docs:
            s3_uri = doc.metadata['source']
            [bucket, s3_key] = s3_uri.split('/', 3)[2:4]
            obj_body = s3.get_object(
                Bucket=bucket,
                Key=s3_key
            )['Body'].read().decode('utf-8')
            doc.page_content = self.strip_chunk_header(obj_body)
            url = doc.metadata['url']
            if url in tmp_docs:
                if doc.metadata['score'] > tmp_docs[url].metadata['score']:
                    tmp_docs[url].metadata['score'] = doc.metadata['score']
            else:
                tmp_docs[url] = doc
        parent_docs = []
        for url in list(tmp_docs.keys()):
            parent_docs.append(tmp_docs[url])
        return parent_docs

    def semantic_search(self, 
        search_recommendations, 
        score_threshold=0.2,
        top_k=10,
        retrieve_parent_docs=False,
        contextual_compression=False
    ):
        docs = self.vector_store_provider.semantic_query(
            search_recommendations, 
            top_k, 
            score_threshold
        )
        return docs

    @staticmethod
    def strip_chunk_header(chunk_text): 
        lines = chunk_text.split('\n')
        final_text = ''
        if lines[0].lower().startswith('<title>') and \
            lines[0].lower().endwith('</title>'):
            final_text = '\n'.join(lines[1:])
        else:
            final_text = chunk_text
        return final_text
          