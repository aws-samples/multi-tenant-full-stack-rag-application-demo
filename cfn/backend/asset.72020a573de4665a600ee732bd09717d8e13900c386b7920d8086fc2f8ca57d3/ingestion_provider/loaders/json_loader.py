#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from datetime import datetime
from copy import deepcopy
from hashlib import md5 

from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status import IngestionStatus
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider import IngestionStatusProvider
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider_factory import IngestionStatusProviderFactory
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders import Loader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter, OptimizedParagraphSplitter


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
        save_vectors_fn: callable,
        emb_provider: EmbeddingsProvider=None, 
        ingestion_status_provider: IngestionStatusProvider=None,
        json_content_fields_order: [str] = default_json_content_fields,
        json_id_fields_order: [str] = default_json_id_fields,
        json_title_fields_order: [str] = default_json_title_fields,
        splitter: Splitter=None,
    ):
        super().__init__()

        self.save_vectors = save_vectors_fn
        if not emb_provider:
            self.emb_provider = EmbeddingsProviderFactory.get_embeddings_provider()
        else:
            self.emb_provider = emb_provider

        if not ingestion_status_provider:
            self.ingestion_status_provider: IngestionStatusProvider = IngestionStatusProviderFactory.get_ingestion_status_provider()
        else:
            self.ingestion_status_provider: IngestionStatusProvider = ingestion_status_provider

        self.json_content_fields_order = json_content_fields_order
        self.json_id_fields_order = json_id_fields_order
        self.json_title_fields_order = json_title_fields_order

        if not splitter:
            self.splitter = OptimizedParagraphSplitter()
        else:
            self.splitter = splitter
        
    def create_ingestion_id(self, json_record, filename, collection_id):
        print(f"create_ingestion_id got {json_record}, {filename}, {collection_id}")
        if isinstance(json_record, str):
            json_record = json.loads(json_record)
        for id_field in self.json_id_fields_order:
            if id_field in list(json_record.keys()):
                return f"{collection_id}/{json_record[id_field]}"
        
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
        print(f"extract_line gotot source {source}")
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
        lines_processed = 1
        status = 'IN_PROGRESS'
        print(f"Saving ingestion status with path {doc_id}")
        ing_status = IngestionStatus(
            user_id,
            doc_id,
            etag,
            lines_processed,
            status
        )
        self.ingestion_status_provider.set_ingestion_status(ing_status)

        if not (content and doc_id and title):
            raise Exception(f"Couldn't find at least one of content ({content}), doc_id ({doc_id}), and title ({title})")
        else:
            print(f"Found doc_id {doc_id}, title {title}, content\n{content}\n\n")
            return VectorStoreDocument.from_dict({
                "id": doc_id,
                "content": content,
                "metadata": meta,
                "vector": self.emb_provider.embed_text(content)
            })
                    
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
                line_ctr = 1
                # jsonlines format
                line = f.readline()
                while line:
                    yield self.extract_line(line.strip(), source, user_id)
                    # if new_doc:
                    #   new_doc.id = f"{filename}:{new_doc.id}:L{line_ctr}"
                    # print(f"Loaded doc {new_doc.to_json()}")
                    # docs.append(new_doc)
                    # line_ctr += 1
                    line = f.readline()

    
    def load_and_split(self, path, user_id, source=None, *, extra_metadata={}, 
        extra_header_text='', json_lines=False, return_dicts=False):
        if not source:
            source = path
        parts = source.split('/')
        print(f"source split to parts {parts}")
        collection_id = parts[-2]
        filename = parts[-1]
        final_docs = []
        docs_processed = 0
        print(f"load_and_split received path {path}, source {source}, collection_id {collection_id}, json_lines {json_lines}")
        for doc in self.load(path, user_id, json_lines, source):
            print(f"self.load yielded doc {doc.to_json()}")
            new_docs= self.split(doc, source, extra_header_text, extra_metadata, return_dicts)
            final_docs += new_docs
            result = self.save_vectors(new_docs, collection_id)
            print(f"Result from saving vector records: {result}")
            docs_processed += result

            # for new_doc in new_docs:
            #     if not 'etag' in new_doc.metadata:
            #         new_doc.metadata['etag'] = md5(new_doc.to_json().encode('utf-8')).hexdigest()
            #     print(f"vectordoc: {new_doc.to_json()}")
            if isinstance(doc, VectorStoreDocument):
                doc = doc.to_dict()

            ing_status = IngestionStatus(
                user_id,
                doc['id'],
                doc['metadata']['etag'],
                1,
                'INGESTED'
            )
            self.ingestion_status_provider.set_ingestion_status(ing_status)
            print(f"Processed {docs_processed} document chunks")
        return final_docs

    def split(self, doc, source, extra_header_text='', extra_metadata={}, return_dicts=False):
        filename = source.split('/')[-1]
        if not 'source' in extra_metadata:
            extra_metadata['source'] = source
        if not 'title' in extra_metadata:
            extra_metadata['title'] = filename
        if 'FILENAME' not in extra_header_text.upper():
            extra_header_text += f"\nFILENAME: {filename}\n{extra_header_text}\n"
            extra_header_text = extra_header_text.replace("\n\n", "\n").lstrip("\n")
        extra_metadata['upsert_date'] = datetime.now().isoformat()
        
        doc = doc.to_dict()
        text_chunks = self.splitter.split(
            doc['content'], 
            doc['id'], 
            extra_header_text=extra_header_text,
            extra_metadata=extra_metadata,
            return_dicts=return_dicts
        )
        ctr = 0
        final_docs = []
        for chunk in text_chunks:
            doc_id = f"{doc['id']}:{ctr}"
            print(f"doc_id is now {doc_id}")
            vector = self.emb_provider.embed_text(chunk)
            if not return_dicts:
                new_doc = VectorStoreDocument(
                    doc_id,
                    chunk,
                    extra_metadata,
                    vector
                )
                print(f"new_doc.to_json() {new_doc.to_json()}")
                final_docs.append(new_doc)
            else:
                new_doc = {
                    'id': doc_id,
                    'content': chunk,
                    'metadata': extra_metadata,
                    'vector': vector
                }
                print(f"new_doc.to_json() {new_doc.to_json()}")
                final_docs.append(new_doc)
            ctr += 1
        return final_docs
        
        

            
