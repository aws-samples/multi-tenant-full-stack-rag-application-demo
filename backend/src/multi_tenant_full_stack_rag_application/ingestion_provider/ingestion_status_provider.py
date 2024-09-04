#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status import IngestionStatus
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider_event import IngestionStatusProviderEvent

"""
GET /ingestion_status/user_id/doc_id: fetch ingestion status
POST /ingestion_status: create or update ingestion status
    body = {
        'user_id': str,
        'doc_id': str,
        'etag': str,
        'lines_processed': int,
        'progress_status': str
    }
DELETE /ingestion_status/user_id/doc_id :  delete an ingestion_status
"""

ddb_client = None
ssm_client = None
ingestion_status_provider = None
ingestion_status_table = None


class IngestionStatusProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        ingestion_status_table: str
    ):
        self.ddb = ddb_client
        self.table = ingestion_status_table
    
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

    def delete_ingestion_status(self, user_id, s3_key):
        doc_id = self.__strip_userid_prefix__(s3_key)
        return self.ddb.delete_item(
            TableName=self.table,
            Key={
                'user_id': {'S': user_id},
                'doc_id': {'S': doc_id}
            }
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
        
        item = None
        status = IngestionStatus(
            user_id, 
            doc_id,
            etag,
            lines_processed,
            progress_status
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

        if handler_evt.method == 'GET':
            response = self.get_ingestion_status(
                handler_evt.user_id, 
                handler_evt.doc_id, 
            )
            print(f"get_ingestion_status response = {response}")
            result = {
                "operation": "GET /ingestion_status",
                "response": self.statuses_to_list(response),
                "statusCode": 200
            }

        elif handler_evt.method == 'POST':
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
            result = {
                "operation": "POST /ingestion_status",
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"]
            }
        
        elif handler_evt.method == 'DELETE':
            print(f"delete_ingestion_status received user_id {handler_evt.user_id}, doc_id {handler_evt.doc_id}")
            response = self.delete_ingestion_status(
                handler_evt.user_id,
                handler_evt.doc_id
            )
            print(f"delete_ingestion_status response {response}")
            result = {
                "operation": "DELETE /ingestion_status",
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
            }
    
        else:
            raise Exception(f'Unexpected method {handler_evt.method}')
        return result

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
        ssm_client = boto3.client('ssm')
        print("About to get ssm parameter for ingestion_status_table")
        ingestion_status_table = ssm_client.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/ingestion_status_table'
        )['Parameter']['Value']
        ingestion_status_provider = IngestionStatusProvider(ddb_client, ingestion_status_table)
    return ingestion_status_provider.handler(event, context)
    