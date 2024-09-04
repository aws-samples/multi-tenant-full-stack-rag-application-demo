#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.ingestion_provider.loaders import Loader
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from datetime import datetime

class TextLoader(Loader):
    def __init__(self, *, emb_provider=None, splitter=None):
        super().__init__()
        self.emb_provider = emb_provider
        self.splitter = splitter
        
    def load(self, path):
        with open(path, 'r') as f:
            return f.read()
    
    def load_and_split(self, path, source=None, *, extra_metadata={}, extra_header_text='', one_doc_per_line=False, return_dicts=False):
        if not source:
            source = path
        filename = path.split('/')[-1]
        content = self.load(path)
        docs = []

        filename = source.split('/')[-1]

        if not 'source' in extra_metadata:
            extra_metadata['source'] = source
        if not 'title' in extra_metadata:
            extra_metadata['title'] = filename
        if 'FILENAME' not in extra_header_text.upper():
            extra_header_text += f"\nFILENAME: {filename}\n{extra_header_text}\n"
            extra_header_text = extra_header_text.replace("\n\n", "\n").lstrip("\n")
        extra_metadata['upsert_date'] = datetime.now().isoformat()
        text_chunks = self.splitter.split(
            content, 
            source, 
            extra_header_text=extra_header_text,
            extra_metadata=extra_metadata,
            return_dicts=return_dicts
        )
        ctr = 0
        id = f"{source}:{ctr}"
        for chunk in text_chunks:
            vector = self.emb_provider.encode(chunk)
            if not return_dicts:
                docs.append(VectorStoreDocument(
                    id,
                    chunk,
                    extra_metadata,
                    vector
                ))
            else:
                docs.append({
                    'id': id,
                    'content': chunk,
                    'metadata': extra_metadata,
                    'vector': vector
                })
            ctr += 1

        return docs

            
