#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from datetime import datetime
from os import getenv
from uuid import uuid4
from .document_collection import DocumentCollection
from .document_collections_handler_event import DocumentCollectionsHandlerEvent
from multi_tenant_full_stack_rag_application.auth_provider import AuthProvider, AuthProviderFactory
from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.ingestion_status_provider import IngestionStatus, IngestionStatusProvider, IngestionStatusProviderFactory
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSetting, UserSettingsProvider, UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response

""" 
API calls served by this function (via API Gateway):
GET /document_collections: list document collections to which a user has access (either owned or shared)
GET /document_collection/{collection_id}?page_size: get a specific doc collection, with paged files.
POST /document_collections: create or update document collections
DELETE /document_collections/{collection_id}: delete a doc collection
DELETE /document_collections/{collection_id}/{file_name}: delete a file from a doc collection
"""

# initialize global vars for the injected clients, so that
# they're only initialized once.

doc_collections_bucket = None
initialized = None
region = None
auth_provider = None
s3 = None
ssm = None
ssp = None
user_settings_provider = None
doc_collections_handler = None


class DocumentCollectionsHandler:
    def __init__(self, 
        auth_provider: AuthProvider,
        ingestion_status_provider: IngestionStatusProvider, 
        s3_client: boto3.client,
        ssm_client: boto3.client,
        system_settings_provider: SystemSettingsProvider,
        user_settings_provider: UserSettingsProvider,
        vector_store_provider: VectorStoreProvider
    ):

        self.auth_provider = auth_provider
        self.ingestion_status_provider = ingestion_status_provider
        self.s3 = s3_client
        self.system_settings_provider = system_settings_provider
        self.user_settings_provider = user_settings_provider
        self.vector_store_provider = vector_store_provider

        origin_domain_name = ssm_client.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']
        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173'
        ]
    
    @staticmethod
    def collections_to_dict(doc_collections):
        final_dict = {}
        if isinstance(doc_collections, list):
            print(f"collections_to_dict received doc collections {doc_collections}")
            for coll in doc_collections:
                if not coll:
                    continue
                else:
                    print(f"Got doc collection {coll}")
                tmp_dict = coll.__dict__()
                final_dict[coll.collection_name] = tmp_dict
        elif isinstance(doc_collections, dict):
            for coll_id in doc_collections:
                coll = doc_collections[coll_id]
                tmp_dict = coll.__dict__()
                final_dict[coll_id] = tmp_dict
        print(f"collections_to_dict returning {final_dict}")
        return final_dict

    @staticmethod
    def create_doc_collection_record(handler_evt):    
        coll_dict = handler_evt.document_collection
        coll_id = uuid4().hex if 'collection_id' not in coll_dict \
            else coll_dict['collection_id']

        created = datetime.now().isoformat() + 'Z' if 'created_date' \
            not in coll_dict else coll_dict['created_date']
        updated = created if 'updated_date' not in coll_dict else \
            coll_dict['updated_date']

        updated = created
        shared_with = [] if 'shared_with' not in coll_dict else coll_dict['shared_with']

        return DocumentCollection(
            coll_dict['user_id'],
            handler_evt.user_email,
            coll_dict['collection_name'],
            coll_dict['description'],
            coll_dict['vector_db_type'],
            coll_id,
            created,
            shared_with,
            updated,
            enrichment_pipelines=json.dumps(coll_dict['enrichment_pipelines'])
        )
    
    def delete_doc_collection(self, handler_evt):
        user_id = handler_evt.user_id
        collection_id = handler_evt.document_collection['collection_id']
        curr_collections = self.get_doc_collections(user_id, include_shared=False)
        final_collections = []
        for coll_name in curr_collections:
            coll = curr_collections[coll_name]
            if coll.user_id != handler_evt.user_id:
                raise Exception(f"User {handler_evt.user_email} doesn't own this document collection, so cannot update it.")
                   
            if coll.collection_id != collection_id:
                final_collections.append(coll)
        
        user_setting = UserSetting(
            user_id, 
            'document_collections', 
            self.collections_to_dict(final_collections)
        )
        self.user_settings_provider.set_user_setting(user_setting)
        self.vector_store_provider.delete_index(collection_id)
        return final_collections

    def delete_file(self, s3_key): 
        self.s3.delete_object(
            Bucket=doc_collections_bucket,
            Key=s3_key
        )
        parts = s3_key.split('/', 2)
        user_id = parts[1]
        ingestion_path = parts[2]
        self.ingestion_status_provider.delete_ingestion_status(user_id, ingestion_path)
        collection_id = ingestion_path.split('/', 1)[0]
        query = {
            "query": {
                "term": {
                "metadata.source.keyword":  ingestion_path
                }
            }
        }
        response = self.vector_store_provider.query(collection_id, query)
        records = response['hits']['hits']
        for record in records:
            self.vector_store_provider.delete_record(collection_id, record['_id'])

    def get_doc_collection(self, owned_by_userid, collection_id, include_shared=True) -> DocumentCollection:
        print(f"get_doc_collection received owned_by_userid {owned_by_userid}, collection_id  {collection_id}")
        doc_collections = self.get_doc_collections(owned_by_userid, include_shared=include_shared)
        #  coll_id = handler_evt.document_collection['collection_id']
        print(f"Got doc collections {doc_collections}, looking for {collection_id}")
        result = None
        for coll_id in doc_collections:
            coll = doc_collections[coll_id]
            if collection_id == coll_id:
                result = coll
                print(f"Found collection {result}")
        return result

    # def get_doc_collections(self, user_id, coll_id=None, user_email='') -> [DocumentCollection]:
    def get_doc_collections(self, user_id, *, include_shared=True):
        print(f"get_doc_collections received user_id {user_id}")
        system_settings = self.system_settings_provider.get_system_settings('user_by_id', user_id)
        system_setting = None
        if len(system_settings) > 0: 
            system_setting = system_settings[0]
        
        collections = {}
        if system_setting != None:
            print(f"get_doc_collections got user_by_id system setting {system_setting}")
            user_email = system_setting.data['user_email']
            collections = self.get_my_doc_collections(user_id, user_email)
            print(f"Got my collections: {collections}")
            if user_email != '' and include_shared:
                shared_collections = self.get_shared_doc_collections(user_id, user_email)
                print(f"Got shared collections {shared_collections}")
                for coll_id in shared_collections:
                    print(f"Got collection {shared_collections[coll_id]}")
                    collections[coll_id] = shared_collections[coll_id] 
        print(f"Get doc collections returning {collections}")
        return collections

    def get_my_doc_collections(self, user_id, user_email) -> [DocumentCollection]:
        print(f"Getting user setting for {user_id}, document_collections")
        user_setting = self.user_settings_provider.get_user_setting(user_id, 'document_collections')
        print(f"Got user setting {user_setting}")
        if user_setting == None:
            return {}
    
        dc_data = user_setting.data
        print(f"Retrieved dc_data {dc_data}")
        doc_collections = {}
        for coll_name in dc_data:
            sub = dc_data[coll_name]
            shared_with = [] if not 'shared_with' in sub else  sub['shared_with']
            # enrichment_pipelines = {} if not 'enrichment_pipelines' in sub else sub['enrichment_pipelines']
            enrichment_pipelines = sub['enrichment_pipelines']
            # graph_schema = {} if not 'graph_schema' in sub else sub['graph_schema']
            graph_schema = sub['graph_schema']
            # args = {
            #     "user_id": user_id, 
            #     "user_email": user_email,
            #     "collection_name": coll_name,
            #     "description": sub['description'],
            #     "vector_db_type": sub['vector_db_type'],
            #     "collection_id": sub['collection_id'],
            #     "shared_with": shared_with,
            #     "created_date": sub['created_date'],
            #     "updated_date": sub['updated_date'],
            #     "enrichment_pipelines": enrichment_pipelines,
            #     "graph_schema": graph_schema,
            # }
            doc_collections[sub['collection_id']] = DocumentCollection(
                user_id, user_email, coll_name, sub['description'],
                sub['vector_db_type'], sub['collection_id'], shared_with, 
                sub['created_date'], sub['updated_date'], 
                enrichment_pipelines=enrichment_pipelines, graph_schema=graph_schema
            )

        return doc_collections

    def get_shared_doc_collections(self, user_id, user_email) -> [DocumentCollection]:
        shared_collections = {}
        shared_with_user = self.system_settings_provider.get_system_settings('user_by_email', user_email)
        if isinstance(shared_with_user, list) and len(shared_with_user) > 0:
            shared_with_user = shared_with_user[0]
            print(f"Got doc collection shared_with_user {shared_with_user}")
            if hasattr( shared_with_user, 'data') and 'document_collections_enabled' in shared_with_user.data:
                collection_refs = shared_with_user.data['document_collections_enabled']
                print(f"Got collection_refs: {collection_refs}")
                for coll_id in collection_refs:
                    coll = collection_refs[coll_id]
                    shared_by_userid = coll['shared_by_userid']
                    shared_collection = self.get_doc_collection(shared_by_userid, coll_id, include_shared=False)
                    print(f"Got collection {shared_collection}")
                    # shared_collection = DocumentCollection(
                    #     user_id,
                    #     user_email,
                    #     coll['collection_name']['S'],
                    #     coll['description']['S'], 
                    #     'shared',
                    #     coll_id,
                    #     [],
                    # )
                    # print(f"created shared_collection {shared_collection}")
                    shared_collections[coll_id] = shared_collection
        print(f"get_shared_doc_collections returning {shared_collections} ")          
        return shared_collections
    
    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = DocumentCollectionsHandlerEvent().from_lambda_event(event)
        print(f"converted to handler_evt {handler_evt}")
        method = handler_evt.method
        path = handler_evt.path
        if handler_evt.origin not in self.frontend_origins:
            return format_response(403, {}, None)
        
        status = 200
        user_id = None
        user_email = None
        if method == 'OPTIONS': 
            result = {}
       
        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            user_id = self.auth_provider.get_userid_from_token(handler_evt.auth_token)
            handler_evt.user_id = user_id
        
        if method == 'GET' and path == '/document_collections':
            doc_collections = self.get_doc_collections(user_id, include_shared=True)
            result = self.collections_to_dict(doc_collections)
            print(f"Got doc collections {result}") 

        elif method == 'GET' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters'):
                return format_response(404, {"Error": "Missing path parameters."}, handler_evt.origin)
            collection_id = handler_evt.path_parameters['collection_id']
            limit = 20 if not (hasattr(handler_evt, 'path_parameters') and 'limit' in handler_evt.path_parameters) else int(handler_evt.path_parameters['limit'])
            last_eval_key = None if not (hasattr(handler_evt, 'path_parameters') and 'start_item' in handler_evt.path_parameters) else handler_evt.path_parameters['start_item']
            if last_eval_key not in ['', None] and not last_eval_key.startswith(collection_id):
                last_eval_key = f"{collection_id}/{last_eval_key}"
            collection =  self.get_doc_collection(user_id, collection_id, include_shared=True)
            print(f"Got collection {collection}")
            collection_obj = self.collections_to_dict([collection])
            ingestion_prefix = f'{collection_obj[list(collection_obj.keys())[0]]["collection_id"]}/'
            file_statuses = self.ingestion_status_provider.get_ingestion_status(user_id, ingestion_prefix, True, limit, last_eval_key)
            print(f"Ingestion_status_provider returned file_statuses {file_statuses}")
            file_list = []
            
            for file_status in file_statuses:
                print(f"Got file_status {file_status}")
                file_list.append({
                    'file_name': file_status['s3_key'].split('/')[-1],
                    'last_modified': datetime.now().isoformat() + 'Z' if not 'last_modified' in file_status else file_status['last_modified'],
                    'status': file_status['progress_status'],
                })
            print(f"file_list is now {file_list}")
            result = { 
                "collection": collection_obj,
                "files": json.dumps(file_list)
            }

        elif method == 'POST' and path == '/document_collections':
            handler_evt.document_collection['user_id'] = user_id
            new_collection_record = self.create_doc_collection_record(handler_evt)
            print(f"Created new collection record {new_collection_record}")
            updated_collections = self.update_doc_collections(new_collection_record, handler_evt)
            result = self.collections_to_dict(updated_collections)
        
        elif method == 'DELETE' and path == '/document_collections': 
            updated_doc_collections = self.delete_doc_collection(handler_evt)
            result = self.collections_to_dict(updated_doc_collections)
        
        elif method == 'DELETE' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters'):
                result = {"Error": "Missing path parameters."}
            else:
                collection_id = handler_evt.path_parameters['collection_id']
                file_name = handler_evt.path_parameters['file_name']
                s3_key = f'private/{user_id}/{collection_id}/{file_name}'
                result = self.delete_file(s3_key)

        return format_response(status, result, handler_evt.origin)

    def update_doc_collections(self, new_collection: DocumentCollection, handler_evt):
        print(f"update_doc_collections got new_collection {new_collection}")
        print(f"update_doc_collections got handler_evt {handler_evt}")

        new_collection_record = new_collection.to_ddb_record()
        
        print(f"after converting to ddb_record: {new_collection_record}")
        doc_collections = self.get_doc_collections(handler_evt.user_id, include_shared=False)
        print(f"update_doc_collections got doc_collections: {doc_collections}")
        final_collections = []
        if doc_collections != []:
            found = False
            for coll_id in doc_collections:
                coll = doc_collections[coll_id]
                print(f"Is collection owned by user_id {handler_evt.user_id}? {new_collection}")
                if coll.user_id != handler_evt.user_id:
                   raise Exception(f"User {handler_evt.user_email} doesn't own this document collection, so cannot update it.")

                if coll.collection_id == new_collection.collection_id:
                    final_collections.append(new_collection)
                    found = True
                else:
                    final_collections.append(coll)
            if not found:
                final_collections.append(new_collection)
        else:
            final_collections = [new_collection]

        user_setting_data = {}
        for coll in final_collections:
            data = coll.__dict__()
            del data['user_id']
            user_setting_data[coll.collection_name] = data
        print(f"Sending user_setting_data {user_setting_data} to UserSettingProvider")
        result = self.user_settings_provider.set_user_setting(UserSetting(
            new_collection.user_id, 
            'document_collections',
            user_setting_data
        ))
        return final_collections

def handler(event, context):
    global doc_collections_bucket, initialized, region, auth_provider, ingestion_status_provider, s3, ssm, ssp, user_settings_provider, doc_collections_handler
    if not initialized:
        region =  getenv('AWS_REGION')
        auth_provider = AuthProviderFactory.get_auth_provider()
        doc_collections_bucket = getenv('DOC_COLLECTIONS_BUCKET')
        ingestion_status_provider = IngestionStatusProviderFactory.get_ingestion_status_provider()
        s3 = BotoClientProvider.get_client('s3')
        ssm = BotoClientProvider.get_client('ssm')
        ssp = SystemSettingsProviderFactory.get_system_settings_provider()
        user_settings_provider = UserSettingsProviderFactory.get_user_settings_provider()
        vector_store_provider: VectorStoreProvider = VectorStoreProviderFactory.get_vector_store_provider()
        doc_collections_handler = DocumentCollectionsHandler(auth_provider, ingestion_status_provider, s3, ssm, ssp, user_settings_provider, vector_store_provider)
        initialized = True 
    result = doc_collections_handler.handler(event, context)
    print(f"document_collections_handler returning {result}")
    return result
