#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
import json
import os

from .loader import Loader
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from multi_tenant_full_stack_rag_application import utils
from datetime import datetime


default_embedding_model = os.getenv('EMBEDDING_MODEL_ID')


class TextLoader(Loader):
    def __init__(self, *, 
        max_tokens_per_chunk: int=0,
        splitter=None
    ):
        super().__init__()
        self.utils = utils
        self.my_origin = self.utils.get_ssm_params('origin_ingestion_provider')

        if max_tokens_per_chunk == 0:
            response = self.utils.get_model_max_tokens(self.my_origin, default_embedding_model)   
            print(f"Got response for model max tokens : {response}")     
            self.max_tokens_per_chunk = json.loads(response['body'])['response']
        else:
            self.max_tokens_per_chunk = max_tokens_per_chunk
        
        if not splitter:
            self.splitter = OptimizedParagraphSplitter(
                max_tokens_per_chunk=self.max_tokens_per_chunk
            )
        else: 
            self.splitter = splitter

    def estimate_tokens(self, text):
        return self.utils.get_token_count(text)
      
    def load(self, path):
        print(f"loading path {path}")
        if path.startswith('s3://'):
            parts = path.split('/')
            bucket = parts[2]
            s3_path = '/'.join(parts[3:])
            local_file = self.utils.download_from_s3(bucket, s3_path)
        else:
            local_file = path
        with open(local_file, 'r') as f_in:
            return f_in.read()
    
    def load_and_split(self, path, user_id, source=None, *, etag='', extra_metadata={}, extra_header_text='', return_dicts=False):
        if not source:
            source = path
        collection_id = source.split('/')[-2]
        filename = path.split('/')[-1]

        self.utils.set_ingestion_status(
            user_id, 
            f"{collection_id}/{filename}",
            etag,
            0, 
            'IN_PROGRESS',
            self.utils.get_ssm_params('origin_ingestion_provider')
        )
        try: 
            content = self.load(path)
            docs = []
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
                extra_metadata=extra_metadata
            )
            ctr = 0
            id = f"{source}:{ctr}"
            for chunk in text_chunks:
                id = f"{source}:{ctr}"
                vector = self.utils.embed_text(chunk, self.my_origin)
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
    
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.utils.set_ingestion_status(
                user_id, 
                f"{collection_id}/{filename}",
                etag,
                0, 
                f'ERROR: {e.__dict__}',
                self.utils.get_ssm_params('origin_ingestion_provider')
            )
            raise e
            
