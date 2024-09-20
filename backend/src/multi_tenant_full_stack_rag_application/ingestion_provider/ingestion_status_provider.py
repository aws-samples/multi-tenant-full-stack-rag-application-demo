#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from .ingestion_status import IngestionStatus
from .ingestion_status_provider_event import IngestionStatusProviderEvent
from multi_tenant_full_stack_rag_application import utils

"""
API 
event {
    "operation": ["get_ingestion_status" | "create_ingestion_status"],
    "origin": the function name of the calling function, or the frontend_origin.,
    "args": 
        for create_ingestion_status:
            "user_id": str,
            "doc_id": str,
            "etag": str,
            "lines_processed": int,
            "progress_status": str

        for delete_ingestion_status:
            "user_id": str,
            "doc_id": str,
            "delete_from_s3": bool=False by default
        
        for get_ingestion_status:
            "user_id": str,
            "doc_id": str
"""

ddb_client = None
ingestion_status_provider = None
ingestion_status_table = None


class IngestionStatusProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        ingestion_bucket: str,
        ingestion_status_table: str,
        s3_client: boto3.client
    ):
        self.utils = utils
        self.ddb = ddb_client
        self.table = ingestion_status_table
        self.s3 = s3_client
        self.allowed_origins = self.utils.get_allowed_origins()
    
    @staticmethod
    def __strip_userid_prefix__(s3_key) -> str: 
        print(f"__strip_userid_prefix__ received {s3_key}")
        if s3_key.startswith('private/'):
            s3_key = s3_key[8:]
        parts = s3_key.split('/')
        print(f"__strip_userid_prefix__ got parts {parts}")
        return_val = ''
        if len(parts) == 2:
            return_val = '/'.join(parts)
        elif len(parts) > 2:
            return_val = '/'.join(parts[1:])
        elif len(parts) == 1:
            return_val = s3_key
        return return_val

    def delete_ingestion_status(self, user_id, doc_id, delete_from_s3=False):
        doc_id = self.__strip_userid_prefix__(doc_id)
        return self.ddb.delete_item(
            TableName=self.table,
            Key={
                'user_id': {'S': user_id},
                'doc_id': {'S': doc_id}
            }
        )
        if delete_from_s3:
            self.s3.delete_object(
                Bucket=os.environ['S3_BUCKET_NAME'],
                Key=f"private/{user_id}/{doc_id}"
            )

    def get_ingestion_status(self, user_id, doc_id, etag='', lines_processed=0, progress_status='IN_PROGRESS', limit=100, last_eval_key=None)-> IngestionStatus:
        projection_expression = "#user_id, #doc_id, #etag, #lines_processed, #progress_status"
        expression_attr_names = {
            "#user_id": "user_id",
            "#doc_id": "doc_id",
            "#etag": "etag",
            "#lines_processed": "lines_processed",
            "#progress_status": "progress_status"
        }

        kwargs = {      
            'TableName': self.table,
            'KeyConditions': {
                'user_id': {
                    'AttributeValueList': [
                        {"S": user_id}
                    ],
                    'ComparisonOperator': 'EQ'
                },
                'doc_id': {
                    'AttributeValueList': [
                        {"S": doc_id}
                    ],
                    'ComparisonOperator': 'BEGINS_WITH'
                }
            },
            'ProjectionExpression': projection_expression,
            'ExpressionAttributeNames': expression_attr_names,
            'Limit': limit
        }
        if last_eval_key: 
            kwargs['ExclusiveStartKey'] = last_eval_key

        result = self.ddb.query(
            **kwargs
        )

        items = []
        if "Item" in result.keys():
            items.append(IngestionStatus.from_ddb_record(result['Item']))
        elif 'Items' in result.keys():
            for item in result['Items']:
                items.append(IngestionStatus.from_ddb_record(item))
        
        print(f"get_ingestion_status returning {items}")
        return items

    def handler(self, event, context):
        print(f"Received event {event}")
        
        handler_evt = IngestionStatusProviderEvent().from_lambda_event(event)

        status = 200
        result = None

        if handler_evt.origin not in self.allowed_origins:
            status = 403
            result = {
                "message": "Forbidden"
            }

        elif handler_evt.operation == 'get_ingestion_status':
            response = self.get_ingestion_status(
                handler_evt.user_id, 
                handler_evt.doc_id, 
            )
            result = self.statuses_to_list(response)
            print(f"get_ingestion_status response = {result}")

        elif handler_evt.operation == 'create_ingestion_status':
            response = self.set_ingestion_status(
                IngestionStatus(
                    handler_evt.user_id,
                    handler_evt.doc_id,
                    handler_evt.etag,
                    handler_evt.lines_processed,
                    handler_evt.progress_status
                )
            )
            print(f"set_ingestion_status response {response}")
            status = response["ResponseMetadata"]["HTTPStatusCode"]
            result = {
                "message": "SUCCESS"
            }
        
        elif handler_evt.operation == 'delete_ingestion_status':
            print(f"delete_ingestion_status received user_id {handler_evt.user_id}, doc_id {handler_evt.doc_id}")
            response = self.delete_ingestion_status(
                handler_evt.user_id,
                handler_evt.doc_id,
                handler_evt.origin,
                delete_from_s3=handler_evt.delete_from_s3
            )
            print(f"delete_ingestion_status response {response}")
            status = response["ResponseMetadata"]["HTTPStatusCode"]
            result = {
                "message": "SUCCESS",
                "deleted_ingestion_status": handler_evt.doc_id
            }
    
        else:
            raise Exception(f'Unexpected method {handler_evt.method}')
        
        return self.utils.format_response(status, result, handler_evt.origin)

    def set_ingestion_status(self, ingestion_status: IngestionStatus): 
        # ingestion_status.doc_id = self.__strip_userid_prefix__(ingestion_status.doc_id)
        result = self.ddb.put_item(
            TableName=self.table,
            Item=ingestion_status.to_ddb_record()
        )
        print(f"set_ingestion_status result = {result}")
        return result
    
    def statuses_to_list(self, statuses: [IngestionStatus]):
        final_list = []
        print(f"statuses_to_list received statuses {statuses}")
        for status in statuses:
            if not status:
                continue
            else:
                print(f"Got status {status}")
            tmp_dict = status.__dict__
            # del tmp_dict['user_id']
            # del tmp_dict['collection_name']
            final_list.append(tmp_dict)
        return final_list


def handler(event, context):
    global ingestion_status_provider
    print(f"initialization handler received event {event}")
    if not ingestion_status_provider:
        ddb_client = boto3.client('dynamodb')
        s3_client = utils.get_s3_client()
        ingestion_bucket = os.getenv('INGESTION_BUCKET')
        ingestion_status_table = os.getenv('INGESTION_STATUS_TABLE')
        ingestion_status_provider = IngestionStatusProvider(ddb_client, ingestion_bucket, ingestion_status_table, s3_client)
    return ingestion_status_provider.handler(event, context)
    