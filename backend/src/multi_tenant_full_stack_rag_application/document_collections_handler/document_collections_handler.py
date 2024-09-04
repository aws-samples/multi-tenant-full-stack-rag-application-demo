#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from datetime import datetime
from os import getenv
from uuid import uuid4
from .document_collection import DocumentCollection
from .document_collections_handler_event import DocumentCollectionsHandlerEvent
from multi_tenant_full_stack_rag_application.utils import BotoClientProvider, format_response

""" 
API calls served by this function (via API Gateway):
GET /document_collections: list document collections to which a user has access (either owned or shared)
GET /document_collection/{collection_id}?page_size: get a specific doc collection, with paged files.
POST /document_collections: create or update document collections
DELETE /document_collections with body {"collection_id": "whatever"}: delete a doc collection
DELETE /document_collections/{collection_id}/{file_name}: delete a file from a doc collection
"""

# initialize global vars for the injected clients, so that
# they're only initialized once.

ingestion_bucket = None
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
        doc_collections_table: str='',
        ddb_client: boto3.client=None,
        lambda_client: boto3.client=None,
        s3_client: boto3.client=None,
        ssm_client: boto3.client=None,
    ):
        if not doc_collections_table:
            self.doc_collections_table = getenv('DOCUMENT_COLLECTIONS_TABLE')
        else:
            self.doc_collections_table = doc_collections_table

        if not ddb_client:
            self.ddb = BotoClientProvider.get_client('dynamodb')
        else:
            self.ddb = ddb_client

        if not lambda_client:
            self.lambda_ = BotoClientProvider.get_client('lambda')
        else:
            self.lambda_ = lambda_client
        
        if not s3_client:
            self.s3 = BotoClientProvider.get_client('s3')
        else:
            self.s3 = s3_client
        
        origin_domain_name = ssm_client.get_parameter(
            Name=f'/{getenv("STACK_NAME")}/frontend_origin'
        )['Parameter']['Value']

        if not origin_domain_name.startswith('http'):
            origin_domain_name = 'https://' + origin_domain_name
        self.frontend_origins = [
            origin_domain_name,
        ]

        self.services = {
                "auth_provider": (ssm_client.get_parameter(
                        Name=f'/{getenv("STACK_NAME")}/auth_provider_api_url'
                    )['Parameter']['Value']
                ),
                "ingestion_status_provider": (ssm_client.get_parameter(
                        Name=f"/{getenv('STACK_NAME')}/ingestion_status_provider_api_url"
                    )['Parameter']['Value']
                ),
                "vector_store_provider": (ssm_client.get_parameter(
                        Name=f'/{getenv("STACK_NAME")}/vector_store_provider_api_url'
                    )['Parameter']['Value']
                )
        }

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
                if not isinstance(coll, dict):
                    coll = coll.__dict__()
                final_dict[coll['collection_name']] = coll
        elif isinstance(doc_collections, dict):
            for coll_id in doc_collections:
                coll = doc_collections[coll_id]
                tmp_dict = coll.__dict__()
                final_dict[coll_id] = tmp_dict
        print(f"collections_to_dict returning {final_dict}")
        return final_dict

    @staticmethod
    def create_doc_collection_record(handler_evt):
        print(f"Create doc collection record got evt {handler_evt.__dict__}")    
        coll_dict = handler_evt.document_collection
        print(f"coll_dict is {coll_dict}")
        coll_id = uuid4().hex if not coll_dict['collection_id'] \
            else coll_dict['collection_id']
        if not 'collection_id' in coll_dict:
            coll_dict['collection_id'] = coll_id
        created = datetime.now().isoformat() + 'Z' if 'created_date' \
            not in coll_dict else coll_dict['created_date']
        updated = created if 'updated_date' not in coll_dict else \
            coll_dict['updated_date']

        updated = created
        shared_with = [] if 'shared_with' not in coll_dict else coll_dict['shared_with']
        if not 'enrichment_pipelines' in coll_dict:
            coll_dict['enrichment_pipelines'] = {}
        print(f"Why is user_email not working? {handler_evt.user_email}, coll {coll_dict}")
        dc = DocumentCollection(
            coll_dict['user_id'],
            coll_dict['user_email'],
            coll_dict['collection_name'],
            coll_dict['description'],
            coll_dict['vector_db_type'],
            coll_id,
            shared_with,
            created,
            updated,
            enrichment_pipelines=json.dumps(coll_dict['enrichment_pipelines'])
        )
        print(f"Created doc collection record {dc.__dict__()}")
        return dc
    
    def delete_doc_collection(self, handler_evt):
        user_id = handler_evt.user_id
        collection_id = handler_evt.document_collection['collection_id']
        collection_name = handler_evt.document_collection['collection_name']
        self.ddb.delete_item(
            TableName=self.doc_collections_table,
            Key={
                'user_id': {'S': user_id},
                'sort_key': {'S': f'collection::{collection_name}'}
            },
            ConditionExpression="#collection_id = :collection_id",
            ExpressionAttributeNames={"#collection_id": "collection_id"},
            ExpressionAttributeValues={":collection_id": {"S": collection_id}}
        )
        return {
            "result": "DELETED",
            "collection_id": collection_id,
            "collection_name": collection_name,
        }

    def delete_file(self, s3_key): 
        self.s3.delete_object(
            Bucket=ingestion_bucket,
            Key=s3_key
        )
        parts = s3_key.split('/', 2)
        user_id = parts[1]
        ingestion_path = parts[2]
        # TODO: change this for the call to the ingestion provider service
        # self.ingestion_status_provider.delete_ingestion_status(user_id, ingestion_path)
        collection_id = ingestion_path.split('/', 1)[0]
        query = {
            "query": {
                "term": {
                "metadata.source.keyword":  ingestion_path
                }
            }
        }
        # TODO replace this with a call to the vector store provider.
        # response = self.vector_store_provider.query(collection_id, query)
        # records = response['hits']['hits']
        # for record in records:
        #     self.vector_store_provider.delete_record(collection_id, record['_id'])

    def get_doc_collection(self, owned_by_userid, collection_id, include_shared=True) -> DocumentCollection:
        print(f"get_doc_collection received owned_by_userid {owned_by_userid}, collection_id  {collection_id}")
        doc_collections = self.get_doc_collections(owned_by_userid, include_shared=include_shared)['response']
        #  coll_id = handler_evt.document_collection['collection_id']
        print(f"Got doc collections {doc_collections}, looking for {collection_id}")
        result = None
        for coll_id in doc_collections:
            coll = doc_collections[coll_id]
            if collection_id == coll_id:
                result = coll
                print(f"Found collection {result}")
        return result

    def get_doc_collections(self, user_id, *, include_shared=True, limit=20, last_eval_key='') -> [DocumentCollection]:
        print(f"get_doc_collections received user_id {user_id}")
        projection_expression = "#user_id, #sort_key, #user_email," + \
            " #collection_name, #description, #vector_db_type," + \
            " #collection_id, #shared_with, #created_date, #updated_date," + \
            " #enrichment_pipelines, #graph_schema"
        expression_attr_names = {
            "#user_id": "user_id",
            "#sort_key": "sort_key", 
            "#user_email": "user_email",
            "#collection_name": "collection_name",
            "#description": "description", 
            "#vector_db_type": "vector_db_type",
            "#collection_id": "collection_id", 
            "#shared_with": "shared_with", 
            "#created_date": "created_date", 
            "#updated_date": "updated_date",
            "#enrichment_pipelines": "enrichment_pipelines", 
            "#graph_schema": "graph_schema"
        }
        sort_key = 'collection::'
        print(f"Getting items starting with {sort_key} for user_id {user_id}")
        kwargs = {
            'TableName': self.doc_collections_table,
            'KeyConditions': {
                'user_id': {
                    'AttributeValueList': [
                        {"S": user_id},
                    ],
                    'ComparisonOperator': 'EQ' 
                }, 
                'sort_key': {
                    'AttributeValueList': [
                        {"S": sort_key},
                    ],
                    'ComparisonOperator': 'BEGINS_WITH' 
                }
            },
            'ProjectionExpression': projection_expression,
            'ExpressionAttributeNames': expression_attr_names,
            'Limit': int(limit)
        }
        if last_eval_key != '':
            kwargs['ExclusiveStartKey']: last_eval_key
        print(f"querying ddb with kwargs {kwargs}")
        result = self.ddb.query(
            **kwargs
        )
        items = []
        print(f"result from querying ddb: {result}")
        if "Items" in result.keys():
            for item in result["Items"]:        
                if len(list(item.keys())) > 0:
                    print(f"About to call DocumentCollection.from_ddb_record for item {item}")
                    doc_collection =  DocumentCollection.from_ddb_record(item)
                    items.append(doc_collection)
        print(f"Returning items {items}")
        return {
            "response": items,
            "last_eval_key": result.get("LastEvaluatedKey", None)
        }
    # def get_doc_collections(self, user_id, *, include_shared=True):
    #     print(f"get_doc_collections received user_id {user_id}")
    #             projection_expression = "#data, #user_id, #setting_name"

    #     result = self.ddb.query(
    #         TableName=self.doc_collections_table,
    #         KeyConditionExpression='user_id = :user_id, sort_key = :sort_key',
    #         ExpressionAttributeValues={
    #             ':user_id': {'S': user_id},
    #             ':sort_key': 
    #         }
    #     )
    #     # TODO replace this with calls to the document collections table
    #     # system_settings = self.system_settings_provider.get_system_settings('user_by_id', user_id)
    #     # system_setting = None
    #     # if len(system_settings) > 0: 
    #     #     system_setting = system_settings[0]
        
    #     # collections = {}
    #     # if system_setting != None:
    #     #     print(f"get_doc_collections got user_by_id system setting {system_setting}")
    #     #     user_email = system_setting.data['user_email']
    #     #     collections = self.get_my_doc_collections(user_id, user_email)
    #     #     print(f"Got my collections: {collections}")
    #     #     if user_email != '' and include_shared:
    #     #         shared_collections = self.get_shared_doc_collections(user_id, user_email)
    #     #         print(f"Got shared collections {shared_collections}")
    #     #         for coll_id in shared_collections:
    #     #             print(f"Got collection {shared_collections[coll_id]}")
    #     #             collections[coll_id] = shared_collections[coll_id] 
    #     # print(f"Get doc collections returning {collections}")
    #     # return collections

    def get_my_doc_collections(self, user_id, user_email) -> [DocumentCollection]:
        print(f"Getting user setting for {user_id}, document_collections")
        # TODO replace this with a call to the doc collections table
        # user_setting = self.user_settings_provider.get_user_setting(user_id, 'document_collections')
        # print(f"Got user setting {user_setting}")
        # if user_setting == None:
        #     return {}
    
        # dc_data = user_setting.data
        # print(f"Retrieved dc_data {dc_data}")
        # doc_collections = {}
        # for coll_name in dc_data:
        #     sub = dc_data[coll_name]
        #     shared_with = [] if not 'shared_with' in sub else  sub['shared_with']
        #     # enrichment_pipelines = {} if not 'enrichment_pipelines' in sub else sub['enrichment_pipelines']
        #     enrichment_pipelines = sub['enrichment_pipelines']
        #     # graph_schema = {} if not 'graph_schema' in sub else sub['graph_schema']
        #     graph_schema = sub['graph_schema']
        #     # args = {
        #     #     "user_id": user_id, 
        #     #     "user_email": user_email,
        #     #     "collection_name": coll_name,
        #     #     "description": sub['description'],
        #     #     "vector_db_type": sub['vector_db_type'],
        #     #     "collection_id": sub['collection_id'],
        #     #     "shared_with": shared_with,
        #     #     "created_date": sub['created_date'],
        #     #     "updated_date": sub['updated_date'],
        #     #     "enrichment_pipelines": enrichment_pipelines,
        #     #     "graph_schema": graph_schema,
        #     # }
        #     doc_collections[sub['collection_id']] = DocumentCollection(
        #         user_id, user_email, coll_name, sub['description'],
        #         sub['vector_db_type'], sub['collection_id'], shared_with, 
        #         sub['created_date'], sub['updated_date'], 
        #         enrichment_pipelines=enrichment_pipelines, graph_schema=graph_schema
        #     )

        # return doc_collections

    def get_shared_doc_collections(self, user_id, user_email) -> [DocumentCollection]:
        shared_collections = {}
        # TODO replace with call to doc collections table
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
    
    def get_userid_from_token(self, jwt):
        # todo
        # invoke cognito auth provider for this one
        print("Should not log this because it's patched right now.")
        pass

    def handler(self, event, context):
        print(f"Got event {event}")
        handler_evt = DocumentCollectionsHandlerEvent().from_lambda_event(event)
        print(f"converted to handler_evt {handler_evt.__dict__}")
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
            # TODO change this with a call to the auth provider service
            # user_id = self.auth_provider.get_userid_from_token(handler_evt.auth_token)
            user_id = self.get_userid_from_token(handler_evt.auth_token)
            print(f"Got user_id {user_id} from auth_token {handler_evt.auth_token}")
            if not user_id:
                raise Exception("Failed to get user_id from the jwt sent in the event.")
            handler_evt.user_id = user_id
        
        if method == 'GET' and path == '/document_collections':
            print("Getting all doc collections")
            doc_collections = self.get_doc_collections(user_id, include_shared=True)['response']
            result = self.collections_to_dict(doc_collections)
            print(f"Got doc collections {result}") 

        elif method == 'GET' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters'):
                return format_response(404, {"Error": "Missing path parameters."}, handler_evt.origin)
            collection_id = handler_evt.path_parameters['collection_id']
            print(f"Got collection_id {collection_id} from path parameters {handler_evt.path_parameters}")

            limit = 20 if not (hasattr(handler_evt, 'path_parameters') and 'limit' in handler_evt.path_parameters) else int(handler_evt.path_parameters['limit'])
            last_eval_key = None if not (hasattr(handler_evt, 'path_parameters') and 'start_item' in handler_evt.path_parameters) else handler_evt.path_parameters['start_item']
            if last_eval_key not in ['', None] and not last_eval_key.startswith(collection_id):
                last_eval_key = f"{collection_id}/{last_eval_key}"
            collection =  self.get_doc_collection(user_id, collection_id, include_shared=True)
            print(f"GET /document_collections {collection.__dict__()}")
            collection_obj = self.collections_to_dict([collection])
            if not collection_obj or len(list(collection_obj.keys())) == 0:
                return format_response(404, {"Error": "Collection not found."}, handler_evt.origin)
            
            ingestion_prefix = f'{collection_obj[list(collection_obj.keys())[0]]["collection_id"]}/'
            # TODO change this to call to ingestion_status_provider
            # file_statuses = self.ingestion_status_provider.get_ingestion_status(user_id, ingestion_prefix, True, limit, last_eval_key)
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
            print(f"creating doc collection from event {handler_evt}")
            new_collection_record = self.create_doc_collection_record(handler_evt)
            print(f"Created new collection record {new_collection_record}")
            upserted_collection = self.upsert_doc_collection(new_collection_record, handler_evt)
            print(f"Upserted collection {upserted_collection}")
            result = self.collections_to_dict([upserted_collection])
            print(f"Result from POST /document_collections {result}")

        elif method == 'DELETE' and path == '/document_collections': 
            deleted_doc_collection_id = self.delete_doc_collection(handler_evt)
            result = deleted_doc_collection_id
        
        # DELETE /document_collections/{collection_id}/{file_name}: deletes a file
        elif method == 'DELETE' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters'):
                result = {"Error": "Missing path parameters."}
            else:
                collection_id = handler_evt.path_parameters['collection_id']
                file_name = handler_evt.path_parameters['file_name']
                s3_key = f'private/{user_id}/{collection_id}/{file_name}'
                result = self.delete_file(s3_key)

        return format_response(status, result, handler_evt.origin)

    def invoke_service(self, service_name, args):
        pass

    def upsert_doc_collection(self, new_collection: DocumentCollection, handler_evt):
        print(f"upsert_doc_collection got new_collection {new_collection}")
        print(f"upsert_doc_collection got handler_evt {handler_evt}")

        new_collection_record = new_collection.to_ddb_record()
        
        response = self.ddb.put_item(
            TableName=self.doc_collections_table,
            Item=new_collection_record
        )
        print(f"Got response from ddb.put_item for new_collection_record \n{new_collection_record}\n{response}")
        if 'ResponseMetadata' in response and \
            'HTTPStatusCode' in response['ResponseMetadata'] and \
                response['ResponseMetadata']['HTTPStatusCode'] == 200:
                result = DocumentCollection.from_ddb_record(new_collection_record)
                print(f"returning DocumentCollection {result}")
                return result
        else:
            raise Exception(f"Failed to upsert collection for {new_collection.__dict__()}.")
        
        # print(f"after converting to ddb_record: {new_collection_record}")
        # doc_collections = self.get_doc_collections(handler_evt.user_id, include_shared=False)['response']
        # print(f"update_doc_collections got doc_collections: {doc_collections}")
        # final_collections = []
        # if doc_collections != []:
        #     found = False
        #     for coll_id in doc_collections:
        #         coll = doc_collections[coll_id]
        #         print(f"Is collection owned by user_id {handler_evt.user_id}? {coll}\nType: {type(coll)}")
        #         if coll.user_id != handler_evt.user_id:
        #            raise Exception(f"User {handler_evt.user_email} doesn't own this document collection, so cannot update it.")

        #         if coll.collection_id == new_collection.collection_id:
        #             final_collections.append(new_collection)
        #             found = True
        #         else:
        #             final_collections.append(coll)
        #     if not found:
        #         final_collections.append(new_collection)
        # else:
        #     final_collections = [new_collection]

        # user_setting_data = {}
        # for coll in final_collections:
        #     data = coll.__dict__()
        #     del data['user_id']
        #     user_setting_data[coll.collection_name] = data
        # print(f"Sending user_setting_data {user_setting_data} to UserSettingProvider")
        # TODO replace with call to doc collections table.
        # result = self.user_settings_provider.set_user_setting(UserSetting(
        #     new_collection.user_id, 
        #     'document_collections',
        #     user_setting_data
        # ))
        # return final_collections

def handler(event, context):
    global ingestion_bucket, initialized, region, auth_provider, ingestion_status_provider, s3, ssm, ssp, user_settings_provider, doc_collections_handler
    if not initialized:
        region =  getenv('AWS_REGION')
        # auth_provider = AuthProviderFactory.get_auth_provider()
        ingestion_bucket = getenv('INGESTION_BUCKET')
        # ingestion_status_provider = IngestionStatusProviderFactory.get_ingestion_status_provider()
        s3 = BotoClientProvider.get_client('s3')
        ssm = BotoClientProvider.get_client('ssm')
        # ssp = SystemSettingsProviderFactory.get_system_settings_provider()
        # user_settings_provider = UserSettingsProviderFactory.get_user_settings_provider()
        # vector_store_provider: VectorStoreProvider = VectorStoreProviderFactory.get_vector_store_provider()
        doc_collections_handler = DocumentCollectionsHandler(auth_provider, ingestion_status_provider, s3, ssm, ssp, user_settings_provider, vector_store_provider)
        initialized = True 
    result = doc_collections_handler.handler(event, context)
    print(f"document_collections_handler returning {result}")
    return result
