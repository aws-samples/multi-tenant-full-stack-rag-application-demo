#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from datetime import datetime
from importlib import import_module
from math import floor
from urllib.parse import unquote_plus

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider import CognitoAuthProvider
from multi_tenant_full_stack_rag_application.document_collections_handler import (
    DocumentCollectionsHandler, DocumentCollectionsHandlerEvent, DocumentCollectionsHandlerFactory
)
from multi_tenant_full_stack_rag_application.ingestion_status_provider import (
    IngestionStatus, IngestionStatusProvider, IngestionStatusProviderFactory
)
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.loaders.json_loader import JsonLoader
from multi_tenant_full_stack_rag_application.vector_store_provider.loaders.pdf_image_loader import PdfImageLoader
from multi_tenant_full_stack_rag_application.vector_store_provider.loaders.text_loader import TextLoader
from multi_tenant_full_stack_rag_application.vector_store_provider.splitters.optimized_paragraph_splitter import OptimizedParagraphSplitter
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_ingestion_handler_event import VectorIngestionHandlerEvent
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory


# default_json_content_fields = [
#     "page_content", "content", "text"
# ]
# default_json_id_fields = [
#     'id','url', 'source'
# ]
# default_json_title_fields = [
#     'title', 'url', 'source'
# ]

default_ocr_model = os.getenv('OCR_MODEL_ID')

max_download_attempts = 3


class VectorIngestionHandler:
    def __init__(self, 
        doc_collections_handler: DocumentCollectionsHandler,
        ingestion_status_provider: IngestionStatusProvider,
        s3_client: boto3.client,
        sqs_client: boto3.client,
        ssm_client: boto3.client,
        system_settings_provider: SystemSettingsProvider,
        vector_store_provider: VectorStoreProvider,
        # json_content_fields_order: [str] = default_json_content_fields,
        # json_id_fields_order: [str] = default_json_id_fields,
        # json_title_fields_order: [str] = default_json_title_fields,
        ocr_model_id: str = default_ocr_model,
        os_batch_size: int=10,
    ):
        self.doc_collections_handler = doc_collections_handler
        self.ingestion_status_provider = ingestion_status_provider
        self.ocr_model_id = ocr_model_id
        self.s3 = s3_client
        self.sqs = sqs_client
        self.system_settings_provider = system_settings_provider
        self.vector_store_provider = vector_store_provider
        self.emb_provider = self.vector_store_provider.embeddings_provider
        # self.json_content_fields_order = json_content_fields_order
        # self.json_id_fields_order = json_id_fields_order
        # self.json_title_fields_order = json_title_fields_order
        self.splitter = OptimizedParagraphSplitter(
            self.emb_provider
        )
        origin_domain_name = ssm_client.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']
        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173'
        ]

    def delete_message(self, rcpt_handle:str, queue_url: str): 
        try: 
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=rcpt_handle)
        except Exception as e:
            print(f"e.args[0] == {e.args[0]}")
            if "NonExistentQueue" in e.args[0]:
                print("CAUGHT ERROR due to non-existent queue in dev")
            elif "ReceiptHandleIsInvalid" in e.args[0]:
                print("CAUGHT ERROR due to non-existent receipt handle in dev.")            
            else:
                raise Exception(f'Error occurred while deleting message: {e.args[0]}')

    def download_s3_file(self, bucket, s3_key, attempts=0):
        if attempts >= max_download_attempts:
            raise Exception(f"Failed to download {s3_key} after {max_download_attempts} attempts.")
        try:
            parts = s3_key.split('/')
            collection_id = parts[-2]
            filename = parts[-1]
            local_path = self.get_tmp_path(collection_id, filename)
            self.s3.download_file(bucket, s3_key, local_path)
            return local_path
        except:
            s3_prefix = '/'.join(s3_key.split('/')[:-1])
            s3_key = f"{s3_prefix}/{unquote_plus(filename)}"
            return self.download_s3_file(bucket, s3_key, attempts + 1)

    # def find_json_content_field(self, local_path):
    #     if not hasattr(self, 'json_content_field'):
    #         json_content_field = ''
    #         with open(local_path, 'r') as json_in:
    #             line = json.loads(json_in.read())
    #             for field in self.json_content_fields_order:
    #                 if field in line:
    #                     self.json_content_field = field
    #                     break
    #     return self.json_content_field

    def find_json_title_field(self, json_dict):
        for field in self.json_title_fields_order:
            if field in json_dict:
                return field
        return ''

    # @staticmethod
    # def get_file_details(file: dict):
    #     bucket = file["bucket"]
    #     s3_key = file["key"]
    #     event_name = file['eventName']
    #     if s3_key.endswith('/'):
    #         return [None, None, None, None, None]
    #     else:
    #         [ignore, user_id, collection_id, filename] = s3_key.split('/', 3)
    #         etag = None
    #         if 'eTag' in record['s3']['object']:
    #             etag = record['s3']['object']['eTag']
            
    #         user_id = unquote_plus(user_id)
    #         # if there's a %253A in the filename it's been double-quoted because
    #         # %25 is a quoted % sign. This happens sometimes when someone uses a quoted 
    #         # URL as a filename
    #         if '%253A' in filename:
    #             filename = unquote_plus(filename)
    #         return [bucket, collection_id, etag, filename, user_id, event_name]

    # def get_metadata(self, record, metadata):
    #     id_key = ''
    #     for key in record:
    #         metadata[key] = record[key]
    #         if id_key == '':
    #             for id_field in self.json_id_fields_order:
    #                 if id_key == '' and key == id_field:
    #                     id_key = key
        
    #     metadata['title'] = record[self.find_json_title_field(record)]
    #     print(f"Found title {metadata['title']}")
    #     metadata['source'] = record[id_key]
    #     if self.json_content_field in metadata:
    #         del metadata[self.json_content_field]
    #     if metadata['source'].startswith('/tmp'):
    #         metadata['source'] = metadata['source'].replace('/tmp/', f's3://{self.bucket}/', 1)
    #     return metadata


    @staticmethod
    def get_queue_url_from_arn(arn: str):
        parts = arn.split(':')
        region = parts[3]
        acct = parts[4]
        name = parts[5]
        return f"https://sqs.{region}.amazonaws.com/{acct}/{name}"

    # @staticmethod
    # def get_title_header(metadata) -> str:
    #     if 'title' not in metadata.keys():
    #         metadata['title'] = metadata['source'].split('/')[-1]
    #     return f"<TITLE>{metadata['title']}</TITLE>\n"

    @staticmethod
    def get_tmp_path(collection_id, file_name):
        if '/' in file_name:
            file_name = file_name.split('/')[-1]
        dir_name = f"/tmp/{collection_id}"
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        final_val = f'{dir_name}/{file_name}'
        return final_val

    def handle_object_created(self, file_dict):
        user_id = file_dict['user_id']
        collection_id = file_dict['collection_id']
        filename = file_dict['filename']

        s3_prefix = f"private/{user_id}/{collection_id}"
        s3_key = f"{s3_prefix}/{filename}"
        print(f"Ingesting {s3_key}")
        
        verified_doc_collection = self.verify_collection(file_dict)
        if not verified_doc_collection:
            print(f"Collection {collection_id} not found for user {user_id}")
            return
        
        local_path = self.download_s3_file(file_dict['bucket'], s3_key)

        # enrichment_pipelines: [str] = verified_doc_collection.enrichment_pipelines
        result = self.ingest_file(local_path, file_dict)  #f"{collection_id}/{filename}" , user_id)
        return result
        # if not s3_key.endswith('.jsonl'):
        #     status_records = self.ingestion_status_provider.get_ingestion_status(user_id, s3_key)
        #     print(f"Got status_records {status_records}")
        #     status = 'IN_PROGRESS'
        #     for status_rec in status_records:
        #         if status_rec and status_rec.progress_status == 'INGESTED' \
        #             and etag == status_rec.etag:
        #             # skip it because it's the same version we already ingested.
        #             status = 'INGESTED'
        #             print(f"Skipping {filename} because it's already complete and hasn't changed")
        #             break
            
        #     if status in ['IN_PROGRESS', 'ENRICHMENT_FAILED']:
        #         print(f"Ingesting file {collection_id}/{filename}")
        #         self.ingestion_status_provider.set_ingestion_status(
        #             IngestionStatus(
        #                 user_id,
        #                 s3_key,
        #                 file['etag'],
        #                 0,
        #                 status
        #             )
        #         )
        #         local_path = self.download_s3_file(bucket, s3_key)
        #         id = f"{collection_id}/{filename}"
    
        #         docs = self.ingest_file(local_path, id)
        #         self.vector_store_provider.save(docs, collection_id)
        #         if id.endswith('.jsonl'):
        #             for doc in docs:
        #                 print(f"Got type of {type(doc)} doc: {doc.to_json()}")
        #                 print(dir(doc)) 
        #                 ing_status = IngestionStatus(user_id, doc.id, file['etag'], 0, 'INGESTED')
        #                 self.ingestion_status_provider.set_ingestion_status(ing_status)
        #         else:                         
        #             ing_status = IngestionStatus(user_id, s3_key, file['etag'], 0, 'INGESTED')
        #             self.ingestion_status_provider.set_ingestion_status(ing_status)
                    
    def handler(self, event, context):
        print(f"VectorIngestionHandler received event {event}")
        handler_evt = VectorIngestionHandlerEvent().from_lambda_event(event)
        print(f"handler_evt is {handler_evt}")
        for file in handler_evt.ingestion_files:
            rcpt_handle = handler_evt.rcpt_handle
            evt_source_arn = handler_evt.evt_source_arn
            queue_url = self.get_queue_url_from_arn(evt_source_arn)
            user_id = file['user_id']
            bucket = file['bucket']
            collection_id = file['collection_id']
            event_name = file['event_name']
            filename = file['filename']
            if 'event' in file and \
                file["event"]== 's3:TestEvent':
                print("Deleting s3:TestEvent")
                self.delete_message(rcpt_handle, queue_url)
                continue

            
            if file['filename'] is None:
                # if the key ends in a / it will come back None.
                # this happens when someone creates a folder in the
                # console.
                print(f"Skipping rec because it's apparently a directory: {rec}")
                continue
            
            if 'ObjectCreated' in event_name:
                result = self.handle_object_created(file)

            elif 'ObjectRemoved' in event_name:
                print(f"Removing file {filename}")
                self.vector_store_provider.delete_record(collection_id, filename)
                self.ingestion_status_provider.delete_ingestion_status(user_id, filename)

            self.delete_message(rcpt_handle, queue_url)
            
        return {
            "status": 200,
            "body": "SUCCESS"
        }

    # ingest_file will pass the call to a loader for that type of file.
    # The loader will yield documents until it's complete. For a multi-document
    # format like jsonlines, that means you'll get one doc back out per
    # line in the file, as a VectorDocument object. 
    def ingest_file(self, local_path, file_dict, extra_meta={}): #  source, user_id, extra_meta={}) -> [VectorStoreDocument]:
        docs = []
        # collection_id = file_dict['collection_id']  # source.split('/')[0]
        if local_path.lower().endswith('.jsonl'):
            docs = self.ingest_json_file(local_path, file_dict, json_lines=True)
        elif local_path.lower().endswith('.json'): 
            docs = self.ingest_json_file(local_path, file_dict, json_lines=False)
        elif local_path.lower().endswith('.pdf'):
            docs = self.ingest_pdf_file(local_path, file_dict)
        else:
            # local_path.endswith('.txt'):
            # assume you can parse it as text for now
            docs = self.ingest_text_file(local_path, file_dict)
        
        # else:
        #     raise Exception(f'unsupported file type: {local_path}\nMore file types coming soon.')
        return docs

    def ingest_json_file(self, local_path, file_dict, *, json_lines=True, extra_meta={}):
        print(f"ingest_json_file got local path {local_path}")
        # if local_path.endswith('.jsonl'):
        #     local_path = self.maybe_fix_jsonl_format(local_path)
        # json_content_field = self.find_json_content_field(local_path)

        # if not json_content_field:
        #     raise Exception(f"Couldn't find any content field in line:\n{line}.")
        
        # the commented options below are defaults, uncomment to change the lists.
        loader = JsonLoader(
            emb_provider=self.emb_provider,
            save_vectors_fn=self.vector_store_provider.save,
            splitter=self.splitter,
            # json_content_fields_order = ["page_content", "content", "text"],
            # json_id_fields_order = ['id','url', 'source'],
            # json_title_fields_order = ['title', 'url', 'source', 'id']
        )
        if not 'etag' in extra_meta:
            extra_meta['etag'] = file_dict['etag']
            
        loader.load_and_split(local_path, file_dict['user_id'], f"{file_dict['collection_id']}/{file_dict['filename']}", extra_metadata=extra_meta, json_lines=json_lines)
        # docs = loader.load_and_split(local_path, user_id, source, extra_metadata=extra_meta, json_lines=json_lines)
        # return docs

    def ingest_pdf_file(self, local_path, file_dict, *, extra_meta={}, ocr_model_id=None):
        print(f"Ingesting pdf file {local_path}")
        if not ocr_model_id:
            ocr_model_id = self.ocr_model_id

        loader = PdfImageLoader(
            save_vectors_fn=self.vector_store_provider.save,
            emb_provider=self.emb_provider,
            ingestion_status_provider=self.ingestion_status_provider,
            ocr_model_id=ocr_model_id, 
            s3=BotoClientProvider.get_client('s3')
        )
        docs = loader.load_and_split(local_path, file_dict['user_id'], f"{file_dict['collection_id']}/{file_dict['filename']}", etag=file_dict['etag'], extra_metadata=extra_meta)
        print(f"ingest_pdf_file returning {docs}")
        return docs

    def ingest_text_file(self, local_path, file_dict, extra_meta={}):
        print(f"Ingesting text file {local_path}")
        loader = TextLoader(
            emb_provider=self.emb_provider, 
            ingestion_status_provider=self.ingestion_status_provider,
            save_vectors_fn=self.vector_store_provider.save,
            splitter=self.splitter
        )
        docs = loader.load_and_split(local_path, file_dict['user_id'], f"{file_dict['collection_id']}/{file_dict['filename']}", extra_metadata=extra_meta)
        print(f"Ingest_text_file returning docs {docs}")
        return docs

    # If you're using scrapy it might spit out content in an array instead of a 
    # single text string, which the JSONLoader doesn't like. flatten any arrays in the
    # incoming object by concatenating the text.
    @staticmethod
    def maybe_fix_jsonl_format(local_path):
        lines_out = ''
        with open(local_path, 'r') as f_in:
            line = json.loads(f_in.readline().strip())
            while line:
                for key in line:
                    if type(line[key]) == list:
                        val = ''
                        for item in line[key]:
                            if val != '':
                                val += ' '
                            val += item
                        line[key] = val
                lines_out += json.dumps(line) + "\n"
                line = f_in.readline().strip()
                if line:
                    line = json.loads(line)
        with open(local_path, 'w') as f_out:
            f_out.write(lines_out)
        return local_path

    # %25 shows up when a percent sign got url quoted
    # which implies that something might have gotten
    # double-quoted if you see %25 in the s3_key.
    def maybe_unquote_s3_key(self, s3_key):
        # %25 is when a percent sign got quoted, which implies that
        # something might have gotten double-quoted.
        if '%25' in s3_key:
            new_key = unquote_plus(s3_key)
            if '%25' in new_key:
                return self.maybe_unquote_s3_uri(new_key)
            else:
                 return new_key
        else:
            return s3_key

    # def set_ingestion_status_batch(docs_batch, status):
    #     for doc in docs_batch:
    #         ing_status = IngestionStatus(
    #             doc.user_id,

    #         )
    # def save_docs(self, out_queue, collection_id, user_id): 
    #     docs_batch = []
    #     doc = out_queue.get()
    #     while doc:
    #         docs_batch.append(doc)
    #         if len(docs_batch) >= self.os_batch_size:
    #             print(f"saving {len(docs_batch)} docs to the vector index", flush=True)
    #             self.vector_store_provider.save(docs_batch, collection_id)
    #             self.set_ingestion_status_batch(
    #                 docs_batch,
    #                 'INGESTED'
    #             )
    #             docs_batch = []
    #         doc = out_queue.get()
        
    #     if len(docs_batch) > 0:
    #         print(f"saving {len(docs_batch)} docs to the vector index", flush=True)
    #         self.vector_store_provider.save(docs_batch,  collection_id)
    #         self.set_ingestion_status_batch(docs_batch, 'INGESTED')
    #     out_queue.put(None)

    def verify_collection(self, file_dict): 
        user_id = file_dict['user_id']
        collection_id = file_dict['collection_id']
        user_by_id_settings = self.system_settings_provider.get_system_settings('user_by_id', user_id)
        user_by_id_setting = None
        verified_doc_collection = False
        if len(user_by_id_settings) > 0:
            user_by_id_setting = user_by_id_settings[0]
        if user_by_id_setting:
            print(f"Got user_by_id_setting {user_by_id_setting}")
            dch_evt = {
                'account_id': file_dict['account_id'],
                'collection_id': collection_id,
                'method': 'GET',
                'path': f'/document_collections/{collection_id}/edit',
                'user_email': user_by_id_setting.data['user_email'],
                'user_id': user_id,
                'origin': self.frontend_origins[0]
            }
            print(f"Got dch_evt dict {dch_evt}")
            dch_evt = DocumentCollectionsHandlerEvent(**dch_evt)
            verified_doc_collection = self.doc_collections_handler.get_doc_collection(user_id, collection_id)
        
        print(f"verified_doc_collection = {verified_doc_collection}")
        
        if not verified_doc_collection: 
            print(f"Error: Invalid document collection {collection_id} received for user {user_id}")
            return False
        else:
            return verified_doc_collection
                

def handler(event, context):
    dch: DocumentCollectionsHandler = DocumentCollectionsHandlerFactory.get_document_collections_handler()
    isp: IngestionStatusProvider = IngestionStatusProviderFactory.get_ingestion_status_provider()
    vsp: VectorStoreProvider = VectorStoreProviderFactory.get_vector_store_provider()
    s3 = BotoClientProvider.get_client('s3')
    sqs = BotoClientProvider.get_client('sqs')
    ssm = BotoClientProvider.get_client('ssm')
    ssp = SystemSettingsProviderFactory.get_system_settings_provider()
    return VectorIngestionHandler(dch, isp, s3, sqs, ssm, ssp, vsp).handler(event, context)
