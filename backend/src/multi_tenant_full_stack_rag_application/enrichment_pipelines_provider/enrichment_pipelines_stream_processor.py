#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os

from multi_tenant_full_stack_rag_application import utils


class EnrichmentPipelinesStreamProcessor:
    def __init__(self, *, sqs_client: boto3.client = None):
        self.utils = utils
        self.my_origin = self.utils.get_ssm_params('origin_enrichment_pipelines_stream_processor')
        
        if not sqs_client:
            self.sqs = self.utils.BotoClientProvider.get_client('sqs')
        else:
            self.sqs = sqs_client
            
        # Get queue URLs from environment variables
        self.entity_extraction_queue_url = os.getenv('ENTITY_EXTRACTION_QUEUE_URL')

    def fetch_document_chunks_from_opensearch(self, doc_id, collection_id):
        """Fetch all chunks for a document from OpenSearch"""
        print(f"Fetching chunks for doc_id: {doc_id} from collection: {collection_id}")
        
        query = {
            "query": {
                "term": {
                    "metadata.source.keyword": doc_id
                }
            },
            "size": 10000
        }
        
        try:
            response = self.utils.vector_store_query(
                collection_id,
                query,
                self.my_origin,
                scroll="10m"
            )
            
            if not response or 'body' not in response:
                print(f"No response or body from vector_store_query for doc_id: {doc_id}")
                return []
                
            body = json.loads(response['body'])
            chunks = body.get('hits', {}).get('hits', [])
            
            print(f"Found {len(chunks)} chunks for doc_id: {doc_id}")
            return chunks
            
        except Exception as e:
            print(f"Error fetching chunks for doc_id {doc_id}: {str(e)}")
            return []

    def process_stream_event(self, event):
        """Process DynamoDB stream events and route to appropriate enrichment queues"""
        print(f"EnrichmentPipelinesStreamProcessor received event: {event}")
        
        for record in event['Records']:
            # Only process INSERT and MODIFY events
            if record['eventName'] not in ['INSERT', 'MODIFY']:
                print(f"Skipping event {record['eventName']}")
                continue
                
            # Check if this is a record we should process
            if 'dynamodb' not in record or 'NewImage' not in record['dynamodb']:
                print(f"Skipping record without NewImage: {record}")
                continue
                
            new_image = record['dynamodb']['NewImage']
            
            # Only process records with AWAITING_ENRICHMENT status
            if ('progress_status' not in new_image or 
                new_image['progress_status']['S'] != 'AWAITING_ENRICHMENT'):
                print(f"Skipping record - not AWAITING_ENRICHMENT: {new_image.get('progress_status', {}).get('S', 'NO_STATUS')}")
                continue
                
            # Extract required fields
            try:
                user_id = new_image['user_id']['S']
                doc_id = new_image['doc_id']['S']
                collection_id = doc_id.split('/')[0]
                etag = new_image['etag']['S']
                lines_processed = new_image['lines_processed']['N']
                
                print(f"Processing enrichment for doc_id: {doc_id}, user_id: {user_id}")
                
                # Get document collection to check which enrichment pipelines are enabled
                response = self.utils.get_document_collections(
                    user_id, 
                    collection_id, 
                    origin=self.my_origin, 
                    consistent=True
                )
                
                if not response:
                    print(f"No collection found for user {user_id}, collection {collection_id}")
                    continue
                    
                collection_name = list(response.keys())[0]
                collection = response[collection_name]
                
                if not collection or 'enrichment_pipelines' not in collection:
                    print(f"No enrichment pipelines configured for collection {collection_id}")
                    continue
                    
                enrichment_pipelines = json.loads(collection['enrichment_pipelines'])
                print(f"Enrichment pipelines configuration: {enrichment_pipelines}")
                
                # get all chunks from the vector database for this doc ID and send separate messages to the 
                # queue for each chunk, because it will 
                # Route to appropriate enrichment queues
                self.route_to_enrichment_queues(
                    enrichment_pipelines,
                    user_id,
                    doc_id,
                    etag,
                    lines_processed,
                    collection_id,
                    collection_name
                )
                
            except Exception as e:
                print(f"Error processing record {record}: {str(e)}")
                continue

    def route_to_enrichment_queues(self, enrichment_pipelines, user_id, doc_id, etag, lines_processed, collection_id, collection_name):
        """Route enrichment requests to appropriate SQS queues based on enabled pipelines"""
        
        # Check if entity extraction is enabled
        if ('entity_extraction' in enrichment_pipelines and 
            enrichment_pipelines['entity_extraction'].get('enabled') == True):
            
            print(f"Routing to entity extraction queue for doc_id: {doc_id}")
            
            # Fetch all chunks for this document from OpenSearch
            chunks = self.fetch_document_chunks_from_opensearch(doc_id, collection_id)
            
            if not chunks:
                print(f"No chunks found for doc_id: {doc_id}, skipping entity extraction")
                return
            
            print(f"Found {len(chunks)} chunks for doc_id: {doc_id}, sending individual messages")
            
            # Send one SQS message per chunk
            messages_sent = 0
            for chunk in chunks:
                try:
                    chunk_id = chunk['_id']
                    chunk_content = chunk['_source']['content']
                    chunk_metadata = chunk['_source'].get('metadata', {})
                    
                    # Create message payload for this specific chunk
                    message_body = {
                        'user_id': user_id,
                        'doc_id': doc_id,
                        'chunk_id': chunk_id,
                        'chunk_content': chunk_content,
                        'chunk_metadata': chunk_metadata,
                        'etag': etag,
                        'lines_processed': lines_processed,
                        'collection_id': collection_id,
                        'collection_name': collection_name,
                        'enrichment_type': 'entity_extraction',
                        'enrichment_config': enrichment_pipelines['entity_extraction']
                    }
                    
                    # Send message to entity extraction queue
                    self.sqs.send_message(
                        QueueUrl=self.entity_extraction_queue_url,
                        MessageBody=json.dumps(message_body),
                        MessageAttributes={
                            'enrichment_type': {
                                'StringValue': 'entity_extraction',
                                'DataType': 'String'
                            },
                            'user_id': {
                                'StringValue': user_id,
                                'DataType': 'String'
                            },
                            'collection_id': {
                                'StringValue': collection_id,
                                'DataType': 'String'
                            },
                            'chunk_id': {
                                'StringValue': chunk_id,
                                'DataType': 'String'
                            }
                        }
                    )
                    messages_sent += 1
                    
                except Exception as e:
                    print(f"Error sending message for chunk {chunk.get('_id', 'unknown')}: {str(e)}")
                    continue
            
            print(f"Successfully sent {messages_sent} messages to entity extraction queue for {doc_id}")
            
            if messages_sent == 0:
                raise Exception(f"Failed to send any messages for doc_id: {doc_id}")
        
        # Future enrichment pipelines can be added here
        # Example:
        # if ('sentiment_analysis' in enrichment_pipelines and 
        #     enrichment_pipelines['sentiment_analysis'].get('enabled') == True):
        #     self.route_to_sentiment_analysis_queue(...)


def handler(event, context):
    """Lambda handler for enrichment pipelines stream processor"""
    processor = EnrichmentPipelinesStreamProcessor()
    processor.process_stream_event(event)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed enrichment pipeline routing')
    }
