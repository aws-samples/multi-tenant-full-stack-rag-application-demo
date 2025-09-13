#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os

from datetime import datetime
from copy import deepcopy
from hashlib import md5 

from .loader import Loader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter, OptimizedParagraphSplitter
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from multi_tenant_full_stack_rag_application import utils


default_embedding_model = os.getenv('EMBEDDING_MODEL_ID')

default_json_content_fields = [
    "page_content", "content", "text"
]
default_json_id_fields = [
    'source', 'id','url', 'filename'
]
default_json_title_fields = [
    'title', 'url', 'source', 'filename', 'id',
]


class JsonLoader(Loader):
    def __init__(self, *, 
        json_content_fields_order: [str] = default_json_content_fields,
        json_id_fields_order: [str] = default_json_id_fields,
        json_title_fields_order: [str] = default_json_title_fields,
        max_tokens_per_chunk: int=0,
        splitter: Splitter=None,
    ):
        super().__init__()

        self.utils = utils
        self.my_origin = self.utils.get_ssm_params("origin_ingestion_provider")

        self.json_content_fields_order = json_content_fields_order
        self.json_id_fields_order = json_id_fields_order
        self.json_title_fields_order = json_title_fields_order

        if max_tokens_per_chunk == 0:
            self.max_tokens_per_chunk = self.utils.get_model_max_tokens(self.my_origin, default_embedding_model)   
        else:
            self.max_tokens_per_chunk = max_tokens_per_chunk

        if not splitter:
            self.splitter = OptimizedParagraphSplitter(
                max_tokens_per_chunk=self.max_tokens_per_chunk
            )
        else:
            self.splitter = splitter
        
    def create_ingestion_id(self, json_record, filename, collection_id):
        print(f"create_ingestion_id got {json_record}, {filename}, {collection_id}")
        if isinstance(json_record, str):
            json_record = json.loads(json_record)
        for id_field in self.json_id_fields_order:
            if id_field in list(json_record.keys()):
                return f"{collection_id}/{filename}:row:{json_record[id_field]}"
        
    def create_content(self, json_record):
        if isinstance(json_record, str):
            json_record = json.loads(json_record)
        for content_field in self.json_content_fields_order:
            if content_field in list(json_record.keys()):
                return json_record[content_field]
        
    def create_title(self, json_record):
        if isinstance(json_record, str):
            json_record = json.loads(json_record)
        for title_field in self.json_title_fields_order:
            if title_field in list(json_record.keys()):
                return json_record[title_field]

    def extract_line(self, jsonline, source, user_id) -> VectorStoreDocument:
        if not jsonline or len(jsonline) == 0:
            return None
        content = None
        doc_id = None
        title = None
        json_obj = json.loads(jsonline)
        print(f"Got line to extract: {json_obj}")
        meta = deepcopy(json_obj)
        keys = list(json_obj.keys())
        print(f"extract_line got source {source}")
        collection_id = source.split('/')[-2]
        filename = source.split('/')[-1]
        doc_id = self.create_ingestion_id(json_obj, filename, collection_id)
        print(f"Created ingestion id {doc_id}")
        title = self.create_title(json_obj)
        print(f"Created title {title}")
        content = self.create_content(json_obj)
        print(f"Created content {content}")

        if not title:
            title = doc_id
        if not 'title' in meta:
            meta['title'] = title
        if not 'source' in meta:
            meta['source'] = source
        
        etag = md5(jsonline.encode('utf-8')).hexdigest()
        meta['etag'] = etag



        if not (content and doc_id and title):
            raise Exception(f"Couldn't find at least one of content ({content}), doc_id ({doc_id}), and title ({title})")
        else:
            print(f"Found doc_id {doc_id}, title {title}, content\n{content}\n\n")

            doc = VectorStoreDocument.from_dict({
                "id": doc_id,
                "content": content,
                "metadata": meta,
                "vector": self.utils.embed_text(content, self.my_origin, 'search_document')
            })
            print(f"vector_ingestion_provider.ingest_file saving doc {doc}")
            self.utils.save_vector_docs([doc],  collection_id, self.my_origin)
        return doc

                    
    def load(self, path, user_id, json_lines=False, source=None):
        if not path: 
            return None
        if not source:
            source = path
        print(f"Loading path {path}, json_lines={json_lines}, source={source}, user_id {user_id}")
        # docs: [VectorStoreDocument] = []
        filename = path.split('/')[-1]
        with open(path, 'r') as f:
            if not json_lines:
                # docs.append(self.extract_line(f.read().replace("\n", "").strip()), source, user_id)
                return self.extract_line(f.read().replace("\n", "").strip(), source, user_id)
            else:
                # jsonlines format
                line = f.readline()
                while line:
                    yield self.extract_line(line.strip(), source, user_id)
                    # if new_doc:
                    #   new_doc.id = f"{filename}:{new_doc.id}:L{line_ctr}"
                    # print(f"Loaded doc {new_doc.to_json()}")
                    # docs.append(new_doc)
                    line = f.readline()

    
    def load_and_split(self, path, user_id, source=None, *, etag='', extra_metadata={}, 
        extra_header_text='', json_lines=False, return_dicts=False):
        if not source:
            source = path
        parts = source.split('/')
        print(f"source split to parts {parts}")
        collection_id = parts[-2]
        filename = parts[-1]
        try: 
            final_docs = []
            docs_processed = 0
            print(f"load_and_split received path {path}, source {source}, collection_id {collection_id}, json_lines {json_lines}")
            for doc in self.load(path, user_id, json_lines, source):
                print(f"self.load yielded doc {doc.to_json()}")
                if return_dicts:
                    doc = doc.to_dict()
                final_docs.append(doc)
                docs_processed += 1
            print(f"Processed {docs_processed} document chunks")
            return final_docs
        
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.utils.set_ingestion_status(
                user_id, 
                f"{collection_id}/{filename}",
                etag,
                0, 
                f'ERROR: {e.__dict__}',
                self.my_origin
            )
            raise e


            
