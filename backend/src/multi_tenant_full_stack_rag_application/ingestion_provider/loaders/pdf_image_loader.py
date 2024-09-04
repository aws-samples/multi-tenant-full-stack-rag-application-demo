#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import shutil
import time

from datetime import datetime
from pdf2image import convert_from_path

from multi_tenant_full_stack_rag_application.bedrock_provider import BedrockProvider
from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider_factory import EmbeddingsProviderFactory
from multi_tenant_full_stack_rag_application.ingestion_provider import IngestionStatus, IngestionStatusProvider, IngestionStatusProviderFactory
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders import Loader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter, OptimizedParagraphSplitter
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument


default_ocr_template_path = 'multi_tenant_full_stack_rag_application/vector_store_provider/loaders/pdf_image_loader_ocr_template.txt'

class PdfImageLoader(Loader):
    def __init__(self,*, 
        save_vectors_fn: callable,
        bedrock_provider: BedrockProvider = None,
        emb_provider: EmbeddingsProvider = None,
        ingestion_status_provider: IngestionStatusProvider = None,
        ocr_model_id: str = None,
        ocr_template_text: str = None,
        s3: boto3.client = None,
        splitter: Splitter = None,
        **kwargs
    ): 
        super().__init__()
        
        self.save_vectors = save_vectors_fn

        if not bedrock_provider:
            self.bedrock_provider = BedrockProvider()
        else:
            self.bedrock_provider = bedrock_provider

        if not emb_provider:
            self.emb_provider = EmbeddingsProviderFactory.get_embeddings_provider()
        else:
            self.emb_provider = emb_provider

        if not ingestion_status_provider:
            self.ingestion_status_provider = IngestionStatusProviderFactory.get_ingestion_status_provider()
        else:
            self.ingestion_status_provider = ingestion_status_provider

        if not s3:
            self. s3 = BotoClientProvider.get_client('s3')
        else:
            self.s3 = s3

        if not splitter:
            self.splitter = OptimizedParagraphSplitter(
                self.emb_provider
            )
        else:
            self.splitter = splitter
    
        if not ocr_model_id:
            self.ocr_model_id = os.getenv('OCR_MODEL_ID')
        else: 
            self.ocr_model_id = ocr_model_id

        if not ocr_template_text:
            with open(default_ocr_template_path, 'r') as f_in:
                self.ocr_template_text = f_in.read()
        else:
            self.ocr_template_text = ocr_template_text

        self.emb_max_tokens = self.emb_provider.get_model_max_tokens()
        print("Max tokens = {self.emb_max_tokens}")

    def download_from_s3(self, bucket, s3_path):
        ts = datetime.now().isoformat()
        tmpdir = f"/tmp/{ts}"
        print(f"Creating tmpdir {tmpdir}")
        os.makedirs(tmpdir)
        filename = s3_path.split('/')[-1].replace(' ', '_')
        local_file_path = f"{tmpdir}/{filename}"
        print(f"Downloading s3://{bucket}/{s3_path} to local_file_path {local_file_path}")
        self.s3.download_file(bucket, s3_path, local_file_path)
        print(f"Success? {os.path.exists(local_file_path)}")
        return local_file_path

    @staticmethod
    def estimate_tokens(text):
        return len(text.split()) * 1.3
    
    def llm_ocr(self, img_paths, parent_filename, extra_header_text, extra_metadata) -> [VectorStoreDocument]:
        results: [VectorStoreDocument] = []
        chunk_num = 0
        page_num = 1
        curr_chunk_text = ''
        curr_chunk_tokens = 0

        file_name_header = f'<FILENAME>\n{parent_filename.split("/")[-1]}\n</FILENAME>\n'
        file_name_header_tokens = self.estimate_tokens(file_name_header)

        for path in img_paths:
            print(f"Processing file {path}")
            page_header = f"<PAGE_NUM>\n{page_num}\n</PAGE_NUM>\n"
            page_header_tokens = self.estimate_tokens(page_header)
            
            chunk_id = f"{parent_filename}:{chunk_num}"

            with open(path, 'rb') as img:
                content = img.read()
            msgs = [
                {
                    "mime_type": "image/jpeg",
                    "content": content
                },
                {
                    "page_num": page_num,
                    "mime_type": "text/plain",
                    "content": f"{file_name_header}\n{page_header}\n{self.ocr_template_text}"
                }
            ]
            response = self.bedrock_provider.invoke_model(
                self.ocr_model_id,
                messages=msgs,
                model_kwargs={
                    "max_tokens": 4096,
                    "temperature": 0.0,
                    "top_p": 0.9,
                    "top_k": 250,
                    "stop_sequences": ["</XML_OUTPUT>"]
                }
            )
            response = response.replace('<XML_OUTPUT>', '').replace('</XML_OUTPUT>', '')
            response_tokens = self.estimate_tokens(response)
            print(f"curr_chunk_tokens: {curr_chunk_tokens}, file_name_header_tokens {file_name_header_tokens}, page_header_tokens {page_header_tokens} = {curr_chunk_tokens + file_name_header_tokens + page_header_tokens}, max {self.emb_max_tokens}")
            if curr_chunk_tokens + file_name_header_tokens + page_header_tokens + \
                response_tokens >= self.emb_max_tokens:
                print(f"Logging with text {curr_chunk_text}, chunk_id {chunk_id}")
                results.append(VectorStoreDocument.from_dict({
                    "id": chunk_id,
                    "content": curr_chunk_text,
                    "vector": self.emb_provider.encode(curr_chunk_text),
                    "metadata": {
                        "title": f"{parent_filename}:{chunk_num}",
                        "page_num": page_num,
                        "source": parent_filename,
                        **extra_metadata
                    }
                }))
                curr_chunk_text = ''
                curr_chunk_tokens = 0
                chunk_num += 1
            else:
                if not file_name_header in curr_chunk_text:
                    curr_chunk_text += file_name_header
                    curr_chunk_tokens += file_name_header_tokens
                if not page_header in curr_chunk_text:
                    curr_chunk_text += page_header
                    curr_chunk_tokens += page_header_tokens
                curr_chunk_text += response
                curr_chunk_tokens += response_tokens

            page_num += 1

        print(f"Logging with text {curr_chunk_text}, chunk_id {chunk_id}")
        results.append(VectorStoreDocument.from_dict({
            "id": f"{parent_filename}:{chunk_num}",
            "content": curr_chunk_text,
            "vector": self.emb_provider.encode(curr_chunk_text),
            "metadata": {
                "title": f"{parent_filename}:{chunk_num}",
                "page_num": page_num,
                "source": parent_filename,
                **extra_metadata
            }
        }))

        # id = f"{parent_filename}:{page_num}"
        # results.append(VectorStoreDocument.from_dict({
        #     "id": id,
        #     "content": header + response,
        #     "vector": self.emb_provider.encode(header + response),
        #     "metadata": {
        #         "title": id,
        #         "page_num": page_num,
        #         "source": parent_filename
        #     }
        # }))
        return results

    def load(self, path):
        if path.startswith('s3://'):
            parts = path.split('/')
            bucket = parts[2]
            s3_path = '/'.join(parts[3:])
            local_file = self.download_from_s3(bucket, s3_path)
        else:
            local_file = path
        print(f"Loaded pdf to {local_file}")
        return local_file

    def load_and_split(self, path, user_id, source=None, *, etag='', extra_metadata={}, extra_header_text=''):
        if not source:
            source = path
        print(f"PdfImageLoader loading {path}, {source}")
        collection_id = source.split('/')[-2]
        filename = source.split('/')[-1]

        ing_status = IngestionStatus(
            user_id, 
            f"{collection_id}/{filename}",
            etag,
            0, 
            'IN_PROGRESS'
        )
        self.ingestion_status_provider.set_ingestion_status(ing_status)
        local_file = self.load(path)
        split_results = self.split_pages(local_file)
        docs: [VectorStoreDocument] = self.llm_ocr(split_results['splits'], source, extra_header_text, extra_metadata)

        self.save_vectors(docs, collection_id)

        ing_status = IngestionStatus(
            user_id,
            f"{collection_id}/{filename}",
            etag,
            1,
            'INGESTED'
        )
        self.ingestion_status_provider.set_ingestion_status(ing_status)

        return docs

    @staticmethod
    def split_pages(local_file):
        print(f"splitting local file {local_file}")
        tmp_dir = '/'.join(local_file.split('/')[0:3]) 
        local_imgs_path = tmp_dir + '/img_splits'
        os.makedirs(local_imgs_path, exist_ok=True)
        print(f"Saving images to {local_imgs_path}")
        convert_from_path(local_file, fmt="jpeg", output_folder=local_imgs_path)
        paths = []
        files = os.listdir(local_imgs_path)
        print(f"Got {len(files)} pages extracted from pdf.")
        for path in files:
            paths.append(f"{local_imgs_path}/{path}")
        paths.sort()
        print(f"{len(paths)} pages to process")

        return {
            "data_type": "image_path",
            "splits": paths
        }

        

            
            
        



