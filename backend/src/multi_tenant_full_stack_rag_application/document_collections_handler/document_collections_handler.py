#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
from datetime import datetime
from os import getenv
from uuid import uuid4
from .document_collection import DocumentCollection
from .document_collections_handler_event import DocumentCollectionsHandlerEvent
from .document_collection_share import DocumentCollectionShare
from multi_tenant_full_stack_rag_application import utils
from urllib.parse import quote_plus

""" 
API calls served by this function (via API Gateway):
GET /document_collections: list all document collections to which a user has access (either owned or shared)
GET /document_collections/{collection_id}: get a specific doc collection, with paged files.
POST /document_collections: create or update document collections
PUT /document_collections/{collection_id}/{share_with_user_email}: share a collection with a user.
DELETE /document_collections/{collection_id}: delete a doc collection
DELETE /document_collections/{collection_id}/{file_name}: delete a file from a doc collection
"""

# initialize global var for the class, so that
# it's only initialized once.

doc_collections_handler = None


class DocumentCollectionsHandler:
    def __init__(self,
        doc_collections_table: str,
        ddb_client: boto3.client=None,
        lambda_client: boto3.client=None,
        s3_client: boto3.client=None,
        ssm_client: boto3.client=None,
    ):
        self.utils = utils
        self.doc_collections_table = doc_collections_table

        if not ddb_client:
            self.ddb = utils.BotoClientProvider.get_client('dynamodb')
        else:
            self.ddb = ddb_client

        if not lambda_client:
            self.lambda_ = utils.BotoClientProvider.get_client('lambda')
        else:
            self.lambda_ = lambda_client

        if not s3_client:
            self.s3 = utils.BotoClientProvider.get_client('s3')
        else:
            self.s3 = s3_client
        
        self.allowed_origins = self.utils.get_allowed_origins()
        self.my_origin = self.utils.get_ssm_params('origin_document_collections_handler')
        
        # origin_domain_name = self.utils.get_ssm_params('origin_frontend', ssm_client=ssm_client)
        # origin_domain_name = ssm_client.get_parameter(
        #     Name=f'/{getenv("STACK_NAME")}/origin_frontend'
        # )['Parameter']['Value']

        # if not origin_domain_name.startswith('http'):
        #     origin_domain_name = 'https://' + origin_domain_name
        # self.allowed_origins = [
        #     origin_domain_name,
        # ]


    @staticmethod
    def collections_to_dict(doc_collections):
        if doc_collections == []:
            return {}
        final_dict = {}
        if isinstance(doc_collections, list):
            # print(f"collections_to_dict received doc collections {doc_collections}")
            for coll in doc_collections:
                if not coll:
                    continue
                if not isinstance(coll, dict):
                    coll = coll.__dict__()
                final_dict[coll['collection_name']] = coll
        elif isinstance(doc_collections, dict):
            for coll_id in doc_collections:
                coll = doc_collections[coll_id]
                tmp_dict = coll.__dict__()
                final_dict[coll_id] = tmp_dict
        # print(f"collections_to_dict returning {final_dict}")
        return final_dict

    @staticmethod
    def create_doc_collection_record(handler_evt):
        # print(f"Create doc collection record got evt {handler_evt.__dict__}")    
        coll_dict = handler_evt.document_collection
        if not 'collection_id' in coll_dict:
            coll_dict['collection_id'] = uuid4().hex

        if not 'graph_schema' in coll_dict: 
            coll_dict['graph_schema'] = {}

        # print(f"coll_dict is {coll_dict}")
        created = datetime.now().isoformat() + 'Z' if 'created_date' \
            not in coll_dict else coll_dict['created_date']
        updated = created if 'updated_date' not in coll_dict else \
            coll_dict['updated_date']

        updated = created
        shared_with = [] if 'shared_with' not in coll_dict else coll_dict['shared_with']
        if not 'enrichment_pipelines' in coll_dict:
            coll_dict['enrichment_pipelines'] = {}
            
        # Make sure the graph schema hasn't changed since our schema data here. This 
        # can happen when working in parallel on Lambda so we want to pull the updated 
        # graph schema from the Doc collection and merge it with the info here.

        dc = DocumentCollection(
            handler_evt.user_id,
            handler_evt.user_email,
            coll_dict['collection_name'],
            coll_dict['description'],
            coll_dict['vector_db_type'],
            coll_dict['vector_ingestion_enabled'],
            coll_dict['file_storage_tool_enabled'],
            coll_dict['collection_id'],
            shared_with,
            created,
            updated,
            enrichment_pipelines=coll_dict['enrichment_pipelines'],
            graph_schema=coll_dict['graph_schema']
        )
        # print(f"Created doc collection record {dc.__dict__()}")
        return dc
    
    def delete_doc_collection(self, handler_evt):
        user_id = handler_evt.user_id
        collection_id = handler_evt.document_collection['collection_id']
        
        response = self.ddb.query(
            TableName=self.doc_collections_table,
            IndexName='by_collection_id',
            KeyConditionExpression='collection_id = :collection_id',
            ExpressionAttributeValues={':collection_id': {'S': collection_id}},
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='#collection_name',
            ExpressionAttributeNames={
                "#collection_name": "collection_name"
            }
        )['Items'][0]
        # print(f"delete_doc_collection got query response {response}")
        collection_name = response['collection_name']['S']

        self.ddb.delete_item(
            TableName=self.doc_collections_table,
            Key={
                'partition_key': {'S': user_id},
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
        
    def delete_file(self, s3_key, delete_from_s3=False):         
        parts = s3_key.split('/', 2)
        user_id = parts[1]
        ingestion_path = parts[2]
        # TODO: change this for the call to the ingestion provider service
        # self.ingestion_status_provider.delete_ingestion_status(user_id, ingestion_path)
       
        my_origin = self.utils.get_ssm_params('origin_document_collections_handler')
        self.utils.delete_ingestion_status(user_id, ingestion_path, my_origin, delete_from_s3=True)

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

    def get_doc_collection(self, owned_by_userid, collection_id, *, consistent=False, include_shared=True) -> DocumentCollection:
        # print(f"get_doc_collection received owned_by_userid {owned_by_userid}, collection_id  {collection_id}")
        doc_collections = self.get_doc_collections(owned_by_userid, consistent=consistent, include_shared=include_shared)["response"]
        #  coll_id = handler_evt.document_collection['collection_id']
        # print(f"Got doc collections {doc_collections}, looking for {collection_id}")
        result = None
        for coll in doc_collections:
            if collection_id == coll.collection_id:
                result = coll
                # print(f"Found collection {result}")
        return result

    def get_doc_collections(self, user_id, *, consistent=False, include_shared=True, limit=20, last_eval_key='') -> [DocumentCollection]:
        # print(f"get_doc_collections received user_id {user_id}")
        if user_id is None:
            return None

        sort_key = 'collection::'
        # print(f"Getting items starting with {sort_key} for user_id {user_id}")
        kwargs = {
            'TableName': self.doc_collections_table,
            'KeyConditions': {
                'partition_key': {
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
            "ConsistentRead": consistent,
            # 'ProjectionExpression': projection_expression,
            # 'ExpressionAttributeNames': expression_attr_names,
            'Limit': int(limit)
        }
        if last_eval_key != '':
            kwargs['ExclusiveStartKey'] = last_eval_key
        print(f"querying ddb with kwargs {kwargs}")
        result = self.ddb.query(
            **kwargs
        )
        items = []
        print(f"result from querying ddb: {result}")
        if "Items" in result.keys():
            for item in result["Items"]:        
                if len(list(item.keys())) > 0:
                    # print(f"About to call DocumentCollection.from_ddb_record for item {item}")
                    doc_collection =  DocumentCollection.from_ddb_record(item)
                    items.append(doc_collection)
        result = {
            "response": items,
            "last_eval_key": result.get("LastEvaluatedKey", None)
        }
        # print(f"get_doc_collections returning value {result}")
        return result

    def get_my_doc_collections(self, user_id, user_email) -> [DocumentCollection]:
        pass
        # print(f"Getting user setting for {user_id}, document_collections")
        # TODO replace this with a call to the doc collections table
        # user_setting = self.user_settings_provider.get_user_setting(user_id, 'document_collections')
        # # print(f"Got user setting {user_setting}")
        # if user_setting == None:
        #     return {}
    
        # dc_data = user_setting.data
        # # print(f"Retrieved dc_data {dc_data}")
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
        # shared_with_user = self.system_settings_provider.get_system_settings('user_by_email', user_email)
        if isinstance(shared_with_user, list) and len(shared_with_user) > 0:
            shared_with_user = shared_with_user[0]
            # print(f"Got doc collection shared_with_user {shared_with_user}")
            if hasattr( shared_with_user, 'data') and 'document_collections_enabled' in shared_with_user.data:
                collection_refs = shared_with_user.data['document_collections_enabled']
                # print(f"Got collection_refs: {collection_refs}")
                for coll_id in collection_refs:
                    coll = collection_refs[coll_id]
                    shared_by_userid = coll['shared_by_userid']
                    shared_collection = self.get_doc_collection(shared_by_userid, coll.collection_id, include_shared=False)
                    # print(f"Got collection {shared_collection}")
                    # shared_collection = DocumentCollection(
                    #     user_id,
                    #     user_email,
                    #     coll['collection_name']['S'],
                    #     coll['description']['S'], 
                    #     'shared',
                    #     coll_id,
                    #     [],
                    # )
                    # # print(f"created shared_collection {shared_collection}")
                    shared_collections[coll_id] = shared_collection
        # print(f"get_shared_doc_collections returning {shared_collections} ")          
        return shared_collections

    def handler(self, event, context):
        print(f"Got event {event}")
        print(f"Got context {context}")
        handler_evt = DocumentCollectionsHandlerEvent().from_lambda_event(event)
        print(f"converted to handler_evt {handler_evt.__dict__}")
        method = handler_evt.method
        path = handler_evt.path

        if handler_evt.origin in self.allowed_origins.values() and \
            handler_evt.origin not in [self.allowed_origins['origin_frontend'], self.allowed_origins['origin_frontend_localdev']] and \
                'user_id' in handler_evt.document_collection:
                # user_id sent in from trusted source that doesn't
                # have access to the user's JWT, like vector_ingestion_provider
                handler_evt.user_id = handler_evt.document_collection['user_id']
                
        elif handler_evt.origin not in self.allowed_origins.values():
            print(f"Couldn't find {handler_evt.origin} in the allowed_origins.values: {self.allowed_origins.values()}")
            return utils.format_response(403, {}, None)
        
        status = 200
        user_email = None
       
        # first check if user_id was sent by a trusted source and use it from there.
        if handler_evt.origin in self.allowed_origins.values() and \
            handler_evt.origin not in [self.allowed_origins['origin_frontend'], self.allowed_origins['origin_frontend_localdev']] and \
                handler_evt.user_id is not None:
                # this means the user_id has been sent
                # by a trusted service that's not receiving
                # the JWT from a user but is receiving
                # a trusted user_id, like the vector_ingestion_provider
                # which gets the user_id from the s3 event, which is from
                # a file written by this app with the trusted user id.
                print(f"Received user_id {handler_evt.user_id} from trusted source")
                
        # if trusted user_id hasn't been sent, get it from the jwt.
        elif hasattr(handler_evt, 'auth_token') and handler_evt.auth_token != '':
            handler_evt.user_id = self.utils.get_userid_from_token(
                handler_evt.auth_token, 
                self.my_origin,
                lambda_client=self.lambda_
            )
            print(f"Got handler_evt.user_id: {handler_evt.user_id}")
            if not handler_evt.user_id:
                raise Exception('Failed to get user_id from JWT.')
            print(f"Got user_id from token {handler_evt.user_id}")
            print(f"Handler_evt is now {handler_evt.__dict__}")
            if hasattr(handler_evt, 'document_collection'):
                handler_evt.document_collection['user_id'] = handler_evt.user_id
            if not handler_evt.user_id or handler_evt.user_id == '':
                raise Exception("Failed to parse auth token")

            # handler_evt.creds = self.utils.get_creds_from_token(
            #     handler_evt.user_id, 
            #     handler_evt.auth_token, 
            #     self.lambda_
            # )
            # print(f"Handler_evt is now {handler_evt.__dict__}") 
        
        print(f"handler_evt is now {handler_evt.__dict__}")
        if method == 'OPTIONS': 
            result = {}

        # all other calls besides options should have user_id set.
        elif not handler_evt.user_id:
            raise Exception("ERROR: No user_id found in event")
            
        elif method == 'GET' and path == '/document_collections':
            # print(f"Getting all doc collections for user_id {handler_evt.user_id}")
            doc_collections_response = self.get_doc_collections(handler_evt.user_id, include_shared=True)
            print(f"Got doc_collections_response {doc_collections_response}")
            result = {
                "response":  {},
                "last_eval_key": doc_collections_response['last_eval_key']
            }
            if len(doc_collections_response["response"]) > 0:
                result["response"] = self.collections_to_dict(doc_collections_response["response"])
            print(f"GET /document_collections returning {result}") 

        elif method == 'GET' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters') or \
                'collection_id' not in handler_evt.path_parameters or \
                   not handler_evt.path_parameters['collection_id']:
                return utils.format_response(404, {"Error": "Missing collection_id parameter."}, handler_evt.origin)
            collection_id = handler_evt.path_parameters['collection_id']
            # print(f"Got collection_id {collection_id} from path parameters {handler_evt.path_parameters}")

            limit = 20 if not (hasattr(handler_evt, 'path_parameters') and \
                'limit' in handler_evt.path_parameters) else \
                    int(handler_evt.path_parameters['limit'])
            last_eval_key = None if not (hasattr(handler_evt, 'path_parameters') and \
                'last_eval_key' in handler_evt.path_parameters) else \
                    handler_evt.path_parameters['last_eval_key']
            if last_eval_key not in ['', None] and not last_eval_key.startswith(collection_id):
                last_eval_key = f"{collection_id}/{last_eval_key}"
            
            collection =  self.get_doc_collection(handler_evt.user_id, collection_id, include_shared=True)
            if not collection:
                result = None
            else:
                print(f"GET /document_collections got {collection.__dict__()}")
                collection_obj = None
                if collection:
                    collection_obj = self.collections_to_dict([collection])
                if not collection_obj or len(list(collection_obj.keys())) == 0:
                    return utils.format_response(404, {"Error": "Collection not found."}, handler_evt.origin)
            
                # ingestion_prefix = quote_plus(
                #     f'{collection_obj[list(collection_obj.keys())[0]]["collection_id"]}'
                # )
                # print(f"Ingestion prefix is {ingestion_prefix}")
                # TODO change this to call to ingestion_status_provider
                # file_statuses = self.ingestion_status_provider.get_ingestion_status(user_id, ingestion_prefix, True, limit, last_eval_key)
                # base_url = f"{self.services['ingestion_status_provider']}/ingestion_status"
                # url = f"{base_url}/{quote_plus(handler_evt.user_id)}/{ingestion_prefix}"
                # creds = self.utils.get_creds_from_token(handler_evt.user_id, handler_evt.auth_token, self.lambda_)
                # print(f"About to get ingested files")
                response = self.utils.invoke_lambda(
                    self.utils.get_ssm_params('ingestion_status_provider_function_name'),
                    {
                        "operation": "get_ingestion_status",
                        "origin": utils.get_ssm_params('document_collections_handler_function_name'),
                        "args": {
                            "user_id": handler_evt.user_id,
                            "doc_id": collection_id,
                            "limit": limit,
                            "last_eval_key": last_eval_key
                        }
                    },
                    lambda_client=self.lambda_
                )
                print(f"Got ingestion status response {response}")
                file_statuses = json.loads(response['body'])
                print(f"Ingestion_status_provider returned file_statuses {file_statuses}")
                file_list = []
                
                for file_status in file_statuses:
                    file_list.append({
                        'file_name': file_status['doc_id'].split('/')[-1],
                        'last_modified': datetime.now().isoformat() + 'Z' \
                            if not 'last_modified' in file_status \
                                else file_status['last_modified'],
                        'status': file_status['progress_status'],
                        # 'presigned_url': file_status['presigned_url']
                    })
                    # file_list.append(file_status)

                # print(f"file_list is now {file_list}")
                result = { 
                    "response": collection_obj,
                    "files": json.dumps(file_list)
                }

        elif method == 'POST' and path == '/document_collections':
            handler_evt.document_collection['user_id'] = handler_evt.user_id
            print(f"creating doc collection from event {handler_evt}")
            new_collection_record = self.create_doc_collection_record(handler_evt)
            print(f"Created new collection record {new_collection_record}")
            upserted_collection = self.upsert_doc_collection(new_collection_record, handler_evt)
            print(f"Upserted collection {upserted_collection}")
            if upserted_collection:
                result = self.collections_to_dict([upserted_collection])
                print(f"Result from POST /document_collections {result}")
            else:
                result = {"Error": "Failed to create collection."}
                status = 500        
        
        elif method == 'PUT' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters') or \
                'collection_id' not in handler_evt.path_parameters or \
                not handler_evt.path_parameters['collection_id'] or \
                'share_with_user_email' not in handler_evt.path_parameters or \
                not handler_evt.path_parameters['share_with_user_email']:
                status = 400
                result = {"Error": "Missing collection_id and/or share_with_user_email parameter."}
            else:
                collection_id = handler_evt.path_parameters['collection_id']
                share_with_user_email = handler_evt.path_parameters['share_with_user_email']
                
        # DELETE /document_collections/{collection_id}: deletes a collection
        # DELETE /document_collections/{collection_id}/{file_name}: deletes a file
        elif method == 'DELETE' and path.startswith('/document_collections/'):
            if not hasattr(handler_evt, 'path_parameters'):
                status = 400
                result = {"Error": "Missing path parameters."}
            else:
                collection_id = handler_evt.path_parameters['collection_id']
                if 'file_name' in handler_evt.path_parameters:
                    # delete a file
                    file_name = handler_evt.path_parameters['file_name']
                    s3_key = f'private/{handler_evt.user_id}/{collection_id}/{file_name}'
                    result = self.delete_file(s3_key, delete_from_s3=True)
                else:
                    # delete a doc collection
                    result = self.delete_doc_collection(handler_evt)
        print(f"Doc collections handler returning result {result}")
        return utils.format_response(status, result, handler_evt.origin)

    def share_create(self, collection_id, share_with_user_email):
        share = DocumentCollectionShare(
            collection_id,
            share_with_user_email,
        )
        self.ddb.put_item(
            TableName=self.doc_collections_table,
            Item=share.to_ddb_record()
        )


    def upsert_doc_collection(self, new_collection: DocumentCollection, handler_evt, *, attempt=1, max_attempts=3):
        # we need to do consistent updates with highly parallel lambda functions
        # running so we don't overwrite the graph schema results from various invocations.
        current_collection = self.get_doc_collection(
            new_collection.user_id, 
            new_collection.collection_id,
            consistent=True
        )
        new_collection_dict = new_collection.__dict__()

        if new_collection.graph_schema != current_collection.graph_schema and \
            current_collection.graph_schema != {}:
            merged_collection = json.loads(json.dumps(current_collection.__dict__()))
            for key in new_collection.graph_schema:
                if key not in merged_collection: 
                    merged_collection[key] = new_collection_dict[key]
                else:
                    # merge the node properties and edge labels
                    for node_prop in new_collection_dict[key]['node_properties']:
                        if node_prop not in merged_collection[key]['node_properties']:
                            merged_collection[key]['node_properties'].append(node_prop)
                    for edge_label in new_collection_dict[key]['edge_labels']:
                        if edge_label not in merged_collection[key]['edge_labels']:
                            merged_collection[key]['edge_labels'].append(edge_label)
            # now we need to do a conditional strongly consistent write, and if it fails we need to 
            # retry this function all.
            try: 
                response = self.ddb.put_item(
                    TableName=self.doc_collections_table,
                    Item=merged_collection.to_ddb_record(),
                    ConsistentWrite=True,
                    ConditionExpression='graph_schema=:graph_schema',
                    ExpressionAttributeValues={
                        ":graph_schema": {"S": current_collection.graph_schema}
                    }
                )
                print(f"Got response from put item {response}")

            except ConditionalCheckFailedException:
                # try again
                next_attempt = attempt + 1
                if next_attempt <= max_attempts:
                    print(f"Graph schema changed while we were updating...retrying attempt {next_attempt}")
                    response = self.upsert_doc_collection(new_collection, handler_evt, next_attempt, max_attempts)
                else:
                    raise Exception(f'Collection graph schema never stabilized in {max_attempts} attempts')
        else: 
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

def handler(event, context):
    global doc_collections_handler
    if not doc_collections_handler:
        doc_collections_table = getenv('DOCUMENT_COLLECTIONS_TABLE')
        region =  getenv('AWS_REGION')
        # ingestion_
        #  = getenv('INGESTION_BUCKET')
        ddb = utils.BotoClientProvider.get_client('dynamodb')
        lambda_ = utils.BotoClientProvider.get_client('lambda')
        s3 = utils.BotoClientProvider.get_client('s3')
        ssm = utils.BotoClientProvider.get_client('ssm')
        doc_collections_handler = DocumentCollectionsHandler(
            doc_collections_table, 
            ddb, 
            lambda_,
            s3, 
            ssm
        )
    result = doc_collections_handler.handler(event, context)
    # print(f"document_collections_handler returning {result}")
    return result
