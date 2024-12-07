#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
import shutil
import time

from base64 import b64encode
from datetime import datetime
from pdf2image import convert_from_path

from multi_tenant_full_stack_rag_application import utils 
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders import Loader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter, OptimizedParagraphSplitter
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument


default_ocr_template_path = 'multi_tenant_full_stack_rag_application/ingestion_provider/loaders/pdf_image_loader_ocr_template.txt'
default_ocr_model = os.getenv('OCR_MODEL_ID')
default_embedding_model = os.getenv('EMBEDDING_MODEL_ID')

class PdfImageLoader(Loader):
    def __init__(self,*, 
        max_tokens_per_chunk: int=0,
        ocr_model_id: str = None,
        ocr_template_text: str = None,
        s3: boto3.client = None,
        splitter: Splitter = None,
        **kwargs
    ): 
        # print(f"remaining kwargs: {kwargs}")
        super().__init__(**kwargs)

        self.utils = utils
        self.my_origin = self.utils.get_ssm_params('origin_ingestion_provider')
        
        if not ocr_model_id:
            self.ocr_model_id = default_ocr_model
        else:
            self.ocr_model_id = ocr_model_id

        if not s3:
            self. s3 = self.utils.BotoClientProvider.get_client('s3')
        else:
            self.s3 = s3

        if max_tokens_per_chunk == 0:
            response = self.utils.get_model_max_tokens(self.my_origin, default_embedding_model)   
            print(f"Got response for model max tokens : {response}")     
            self.max_tokens_per_chunk = json.loads(response['body'])['response']
            # self.max_tokens_per_chunk = response['response']
        else:
            self.max_tokens_per_chunk = max_tokens_per_chunk
        
        print(f"Max tokens = {self.max_tokens_per_chunk}")
        if not splitter:
            self.splitter = OptimizedParagraphSplitter(
                max_tokens_per_chunk=self.max_tokens_per_chunk
            )
        else:
            self.splitter = splitter
        # print(f"before checking, ocr_template_text = {ocr_template_text}")
        if not ocr_template_text:
            ocr_template_path = self.get_default_ocr_template_path()
            # print(f"Fetching default ocr_template from {ocr_template_path}")
            with open(ocr_template_path, 'r') as f_in:
                self.ocr_template_text = f_in.read()
        else:
            # print("Using ocr template data passed in.")
            self.ocr_template_text = ocr_template_text
        # print(f"PdfImageLoader initialized with ocr template text {self.ocr_template_text}")

    def estimate_tokens(self, text):
        return self.utils.get_token_count(text)
    
    def get_default_ocr_template_path(self):
        return default_ocr_template_path

    def llm_ocr(self, img_paths, parent_filename, extra_header_text, extra_metadata):
        if not hasattr(self, 'ocr_template_text') or not self.ocr_template_text:
            ocr_template_path = self.get_default_ocr_template_path()
            # print(f"Fetching default ocr_template from {ocr_template_path}")
            with open(ocr_template_path, 'r') as f_in:
                self.ocr_template_text = f_in.read()
        results = []
        chunk_num = 0
        page_num = 1
        curr_chunk_text = ''
        curr_chunk_tokens = 0

        file_name_header = f'<FILENAME>\n{parent_filename.split("/")[-1]}\n</FILENAME>\n'
        file_name_header_tokens = self.estimate_tokens(file_name_header)
        print(f"** Received {len(img_paths)} pages to process **")
        
        for path in img_paths:
            # print(f"Processing file {path}")
            page_header = f"<PAGE_NUM>\n{page_num}\n</PAGE_NUM>\n"
            page_header_tokens = self.estimate_tokens(page_header)
            
            chunk_id = f"{parent_filename}:{chunk_num}"

            with open(path, 'rb') as img:
                content = b64encode(img.read()).decode('utf-8')
                print(f"Type of content is now {type(content)}")
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
            # # print(f"Invoking model with msgs {msgs}")
            response = self.utils.invoke_bedrock(
                "invoke_model",
                {
                    "messages": msgs,
                    "model_id": self.ocr_model_id,
                },
                self.utils.get_ssm_params('origin_ingestion_provider')
            )
            print(f"Got response from invoking model: {response}")
            response = response['response'].replace('<XML_OUTPUT>', '').replace('</XML_OUTPUT>', '')
            response_tokens = self.estimate_tokens(response)
            # print(f"curr_chunk_tokens: {curr_chunk_tokens}, file_name_header_tokens {file_name_header_tokens}, page_header_tokens {page_header_tokens} = {curr_chunk_tokens + file_name_header_tokens + page_header_tokens}, max {self.max_tokens_per_chunk}")
            if curr_chunk_tokens + file_name_header_tokens + page_header_tokens + \
                response_tokens >= self.max_tokens_per_chunk:
                print(f"Logging with text {curr_chunk_text}, chunk_id {chunk_id}")
                results.append(VectorStoreDocument.from_dict({
                    "id": chunk_id,
                    "content": curr_chunk_text,
                    "vector": self.utils.embed_text(curr_chunk_text, self.my_origin),
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
            # print(f"\n\n***Processed page {page_num}***\n\n")
            # page_num += 1

        # print(f"Logging with text {curr_chunk_text}, chunk_id {chunk_id}")
        if curr_chunk_text != '':
            print(f"Final chunk text is {curr_chunk_text}")
            results.append(VectorStoreDocument.from_dict({
                "id": f"{parent_filename}:{chunk_num}",
                "content": curr_chunk_text,
                "vector": self.utils.embed_text(curr_chunk_text, self.my_origin),
                "metadata": {
                    "title": f"{parent_filename}:{chunk_num}",
                    "page_num": page_num,
                    "source": parent_filename,
                    **extra_metadata
                }
            }))
            print(f"\n\n***Processed page {page_num}***\n\n")

        # id = f"{parent_filename}:{page_num}"
        # results.append(VectorStoreDocument.from_dict({
        #     "id": id,
        #     "content": header + response,
        #     "vector": self.utils.embed_text(header + response, self.my_origin),
        #     "metadata": {
        #         "title": id,
        #         "page_num": page_num,
        #         "source": parent_filename
        #     }
        # }))
        
        return results

    def load(self, path):
        print(f"Loading path {path}")
        if path.startswith('s3://'):
            parts = path.split('/')
            bucket = parts[2]
            s3_path = '/'.join(parts[3:])
            local_file = self.utils.download_from_s3(bucket, s3_path)
        else:
            local_file = path
        # print(f"Loaded pdf to {local_file}")
        return local_file

    def load_and_split(self, path, user_id, source=None, *, etag='', extra_metadata={}, extra_header_text=''):
        if not source:
            source = path
        # print(f"PdfImageLoader loading {path}, {source}")
        collection_id = source.split('/')[-2]
        filename = source.split('/')[-1]

        self.utils.set_ingestion_status(
            user_id, 
            f"{collection_id}/{filename}",
            etag,
            0, 
            'IN_PROGRESS',
            self.utils.get_ssm_params('origin_ingestion_provider')
        )
        try:
            print(f"Loading path {path}")
            print(f"does path exist? {os.path.exists(path)}")
            local_file = self.load(path)
            split_results = self.split_pages(local_file)
            docs: [VectorStoreDocument] = self.llm_ocr(split_results['splits'], source, extra_header_text, extra_metadata)
            return docs
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.utils.set_ingestion_status(
                user_id, 
                f"{collection_id}/{filename}",
                etag,
                0, 
                f'ERROR: {e.args[0]}',
                self.utils.get_ssm_params('origin_ingestion_provider')
            )
            raise e
        
        # self.utils.save_vector_docs(docs, user_id, collection_id)

        # ing_status = IngestionStatus(
        #     user_id,
        #     f"{collection_id}/{filename}",
        #     etag,
        #     1,
        #     'INGESTED'
        # )
        # payload['origin'] = self.my_origin
        # self.utils.set_ingestion_status(
        #     user_id,
        #     f"{collection_id}/{filename}",
        #     etag,
        #     1,
        #     'INGESTED',
        #     self.my_origin,
        # )
        return docs

    @staticmethod
    def split_pages(local_file):
        # print(f"splitting local file {local_file}")
        tmp_dir = '/'.join(local_file.split('/')[0:3]) 
        local_imgs_path = tmp_dir + '/img_splits'
        os.makedirs(local_imgs_path, exist_ok=True)
        # print(f"Saving images to {local_imgs_path}")
        convert_from_path(local_file, fmt="jpeg", output_folder=local_imgs_path)
        paths = []
        files = os.listdir(local_imgs_path)
        # print(f"Got {len(files)} pages extracted from pdf.")
        for path in files:
            paths.append(f"{local_imgs_path}/{path}")
        paths.sort()
        # print(f"{len(paths)} pages to process")

        return {
            "data_type": "image_path",
            "splits": paths
        }

        

            
            
        



