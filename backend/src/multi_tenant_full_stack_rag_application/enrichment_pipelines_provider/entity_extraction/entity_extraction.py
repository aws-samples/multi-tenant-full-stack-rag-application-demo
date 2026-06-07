#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
# EntityExtraction watches for changes in the ingestion status
# table. If a record status changes to AWAITING_ENRICHMENT, it performs
# entity extraction and sets the entity extraction status to
# ENRICHMENT_COMPLETE. If it fails, it sets the status to
# ENRICHMENT_FAILED. If the collection doesn't have the entity
# extraction enrichment pipeline enabled, it does nothing.

import base64
import boto3
import json
import os
import shutil

# import multi_tenant_full_stack_rag_application.enrichment_pipelines_provider.entity_extraction.neptune_client as neptune

from multi_tenant_full_stack_rag_application import utils
from multi_tenant_full_stack_rag_application.enrichment_pipelines_provider import Pipeline

# default_entity_extraction_template_path = 'multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/default_entity_extraction_template.txt'
default_extraction_model_id = os.getenv('EXTRACTION_MODEL_ID')
entity_extraction = None


class EntityExtraction(Pipeline):
    def __init__(self, 
        pipeline_name: str, 
        *,
        extraction_prompt_template_id: str=None,
        # neptune_endpoint: str=None,
        # pdf_loader: Loader=None,
        # s3_client: boto3.client=None,
        # splitter: Splitter=None,
        **kwargs
    ):
        super().__init__(pipeline_name, **kwargs)

        self.utils = utils
        # if not neptune_endpoint:
        #     self.neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT')
        # else:
        #     self.neptune_endpoint = neptune_endpoint
        self.my_origin = self.utils.get_ssm_params('origin_entity_extraction')
        self.allowed_origins = self.utils.get_allowed_origins()
        self.model_id = default_extraction_model_id

    def process(self, event):
        print(f"entity_extraction.process received {event}")
        for record in event['Records']:
            # Handle SQS message format instead of DynamoDB stream
            if 'body' not in record:
                print(f"Skipping record without body: {record}")
                continue
                
            try:
                # Parse the SQS message body
                message_body = json.loads(record['body'])
                print(f"Got message body: {message_body}")
                
                # Extract fields from the queue message
                user_id = message_body['user_id']
                doc_id = message_body['doc_id']
                collection_id = message_body['collection_id']
                collection_name = message_body['collection_name']
                etag = message_body['etag']
                lines_processed = message_body['lines_processed']
                enrichment_type = message_body['enrichment_type']
                enrichment_config = message_body['enrichment_config']
                
                # New fields for individual chunk processing
                chunk_id = message_body.get('chunk_id')
                chunk_content = message_body.get('chunk_content')
                chunk_metadata = message_body.get('chunk_metadata', {})
                
                # Verify this is an entity extraction message
                if enrichment_type != 'entity_extraction':
                    print(f"Skipping message - not entity extraction: {enrichment_type}")
                    continue
                
                # Check if this is a new chunk-based message or old file-based message
                if chunk_id and chunk_content:
                    print(f"Processing entity extraction for chunk_id: {chunk_id}, doc_id: {doc_id}, user_id: {user_id}")
                else:
                    print(f"Processing entity extraction for doc_id: {doc_id}, user_id: {user_id} (legacy mode)")
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing message body: {str(e)}")
                continue

            # Get document collection to verify entity extraction is still enabled
            response = self.utils.get_document_collections(user_id, collection_id, origin=self.my_origin, consistent=True)
            # print(f"Got response {response}")
            if not response:
                print(f"Collection {collection_id} not found for user {user_id}")
                continue
                
            collection = response[collection_name]
            if not collection or 'enrichment_pipelines' not in collection:
                print(f"No enrichment pipelines configured for collection {collection_id}")
                continue
                
            enrichment_pipelines = json.loads(collection['enrichment_pipelines'])
            # print(f"enrichment pipelines is now {enrichment_pipelines}")
            if not ('entity_extraction' in enrichment_pipelines and enrichment_pipelines['entity_extraction']['enabled'] == True):
                print(f"Skipping entity extraction for doc collection {collection} because it doesn't have entity extraction enabled.")
                continue

            # Get template and graph schema
            template_id = json.loads(collection['enrichment_pipelines'])["entity_extraction"]["templateIdSelected"]
            response = self.utils.get_prompt_template(
                template_id,
                user_id,
                self.my_origin
            )
            print(f"Got prompt template response {response}")
            template_body = json.loads(response['body'])
            template = template_body[list(template_body.keys())[0]]
            print(f"Got template {template}, type ({type(template)}")
            ee_template_text = template['template_text']
            
            # Get the graph schema using the utils.get_graph_schema function
            graph_schema = self.utils.get_graph_schema(
                user_id,
                collection_name,
                origin=self.my_origin
            )
            graph_schema_json = json.dumps(graph_schema)

            errors = False
            
            # Handle both new chunk-based messages and legacy file-based messages
            if chunk_id and chunk_content:
                # New chunk-based processing - process single chunk
                print(f"Processing single chunk: {chunk_id}")
                
                # Process this single chunk for entity extraction
                prompt = ee_template_text.replace('{context}', chunk_content).replace('{graph_schema}', graph_schema_json)
                prompt = f"<CHUNK_IDS>{chunk_id}</CHUNK_IDS>\n<FILENAME>{doc_id}</FILENAME>\n\n" + prompt
                
                msgs = [{
                    "role": "user",
                    "content": [{"text": prompt}]
                }]
                
                try:
                    chunk_response = self.utils.invoke_bedrock(
                        'invoke_model',
                        {
                            "model_id": self.model_id,
                            "messages": msgs,
                            "inference_config": {
                                "maxTokens": 2000,
                                "temperature": 0.0,
                                "stopSequences": ["</JSON>"] if 'stop_sequences' not in template else template['stop_sequences']
                            }
                        },
                        self.my_origin
                    )
                    
                    response_str = chunk_response['response'].replace('\n', '').replace("\n", "")
                    for stop_seq in template['stop_sequences']:
                        start_seq = stop_seq.replace('</', '<')
                        response_str = response_str.replace(start_seq, '').replace(stop_seq, '').strip()
                    
                    print(f"Chunk {chunk_id} response: {response_str[:200]}...")
                    extraction_result = json.loads(response_str)
                    
                    # Process nodes from this chunk
                    for node in extraction_result.get("nodes", []):
                        if '::' not in node['id']:
                            node['id'] = f"{collection_id}::{node['id']}"
                        
                        # Add chunk reference to node
                        node['from_vector_record_id'] = chunk_id
                        node['from_document'] = doc_id
                        
                        # Create node in Neptune
                        node_id = node['id'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        node_type = node['type'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        
                        merge_statement = f"g.mergeV([(id): '{node_id}']).option(onCreate, [(label):'{node_type}'"
                        
                        # Create a copy to avoid modifying the original
                        node_copy = node.copy()
                        del node_copy['id']
                        del node_copy['type']
                        
                        # Add node properties
                        for key, value in node_copy.items():
                            clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                            clean_value = str(value).replace("\'", "\\\'")
                            merge_statement += f", '{clean_key}': '{clean_value}'"
                        
                        merge_statement += f", 'collection_id': '{collection_id}'"
                        merge_statement += '])'
                        merge_statement += '.option(onMatch, ['
                        
                        # Add onMatch properties
                        for key, value in node_copy.items():
                            clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                            clean_value = str(value).replace("\'", "\\\'")
                            merge_statement += f"'{clean_key}': '{clean_value}',"
                        
                        merge_statement += f" 'collection_id': '{collection_id}'"
                        merge_statement = merge_statement.strip(',') + '])' + '\n'
                        
                        print(f"Creating node: {node_id} ({node_type})")
                        neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                        if not neptune_response:
                            print(f"Failed to create node: {node_id}")
                            errors = True
                            break
                    
                    # Process edges from this chunk
                    for edge in extraction_result.get("edges", []):
                        # Ensure source and target have collection prefix
                        if '::' not in edge['source']:
                            edge['source'] = f"{collection_id}::{edge['source']}"
                        if '::' not in edge['target']:
                            edge['target'] = f"{collection_id}::{edge['target']}"
                        
                        edge['from_vector_record_id'] = chunk_id
                        
                        edge_source = edge['source'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        edge_target = edge['target'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        edge_label = edge['edge_label'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        
                        # Create unique edge ID
                        edge_id = f"{edge_source}::{edge_label}::{edge_target}"
                        edge_id = edge_id.replace('-', '_').replace(' ', '_').replace('/', '_').replace("\'", "\\\'")
                        
                        merge_statement = f"g.mergeE([(id): '{edge_id}'])"
                        merge_statement += f".option(onCreate, [(from): '{edge_source}', (to): '{edge_target}', (T.label): '{edge_label}', weight: 1.0"
                        
                        # Add edge properties if they exist
                        edge_copy = edge.copy()
                        for key in ['source', 'target', 'edge_label']:
                            edge_copy.pop(key, None)
                        
                        for key, value in edge_copy.items():
                            clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                            clean_value = str(value).replace("\'", "\\\'")
                            merge_statement += f", '{clean_key}': '{clean_value}'"
                        
                        merge_statement += "])"
                        merge_statement += f".option(onMatch, [weight: 1.0])\n"
                        
                        print(f"Creating edge: {edge_source} --{edge_label}--> {edge_target}")
                        neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                        if not neptune_response:
                            print(f"Failed to create edge: {edge_id}")
                            errors = True
                            break
                        
                except Exception as e:
                    print(f"Error processing chunk {chunk_id}: {str(e)}")
                    errors = True
                    
            else:
                # Legacy mode - fetch all chunks and process in batches (for backward compatibility)
                print("Processing in legacy mode - fetching all chunks")
                query = {
                    "query": {
                        "term": {
                            "metadata.source.keyword": doc_id
                        }
                    }
                }
                response = self.utils.vector_store_query(
                    collection_id,
                    query,
                    self.my_origin
                )
                body = json.loads(response['body'])
                chunks = body['hits']['hits']
                print(f"Found {len(chunks)} chunks for legacy processing")
                
                # Process chunks in batches for entity extraction
                batch_size = int(os.getenv('ENTITY_EXTRACTION_BATCH_SIZE', '10'))
                all_nodes = []
                all_edges = []
                document_id = doc_id.replace('/', '::', 1).replace('-', '_')

                # Add document node once
                document_node = {
                    "id": document_id,
                    "type": "document",
                    "source": doc_id
                }
                all_nodes.append(document_node)

                # Process chunks in batches
                for batch_start in range(0, len(chunks), batch_size):
                    batch_end = min(batch_start + batch_size, len(chunks))
                    batch_chunks = chunks[batch_start:batch_end]
                    
                    print(f"Processing batch {batch_start//batch_size + 1}: chunks {batch_start + 1}-{batch_end}")
                    
                    # Aggregate text content from this batch
                    batch_text = ""
                    batch_chunk_ids = []
                    
                    for hit in batch_chunks:
                        chunk_content = hit['_source']['content']
                        chunk_id = hit['_id']
                        batch_chunk_ids.append(chunk_id)
                        
                        # Add chunk separator and content
                        batch_text += f"\n\n--- CHUNK {chunk_id} ---\n{chunk_content}"
                    
                    # Process this batch for entity extraction
                    prompt = ee_template_text.replace('{context}', batch_text).replace('{graph_schema}', graph_schema_json)
                    prompt = f"<CHUNK_IDS>{','.join(batch_chunk_ids)}</CHUNK_IDS>\n<FILENAME>{doc_id}</FILENAME>\n\n" + prompt
                    
                    msgs = [{
                        "role": "user",
                        "content": [{"text": prompt}]
                    }]
                    
                    try:
                        batch_response = self.utils.invoke_bedrock(
                            'invoke_model',
                            {
                                "model_id": self.model_id,
                                "messages": msgs,
                                "inference_config": {
                                    "maxTokens": 2000,
                                    "temperature": 0.0,
                                    "stopSequences": ["</JSON>"] if 'stop_sequences' not in template else template['stop_sequences']
                                }
                            },
                            self.my_origin
                        )
                        
                        response_str = batch_response['response'].replace('\n', '').replace("\n", "")
                        for stop_seq in template['stop_sequences']:
                            start_seq = stop_seq.replace('</', '<')
                            response_str = response_str.replace(start_seq, '').replace(stop_seq, '').strip()
                        
                        print(f"Batch {batch_start//batch_size + 1} response: {response_str[:200]}...")
                        batch_extraction_result = json.loads(response_str)
                        
                        # Process nodes from this batch
                        for node in batch_extraction_result.get("nodes", []):
                            if '::' not in node['id']:
                                node['id'] = f"{collection_id}::{node['id']}"
                            
                            # Add batch reference to node (using first chunk ID as representative)
                            node['from_vector_record_id'] = batch_chunk_ids[0] if batch_chunk_ids else 'unknown'
                            node['from_document'] = doc_id
                            node['batch_chunk_ids'] = ','.join(batch_chunk_ids)
                            all_nodes.append(node)
                        
                        # Add edges from this batch
                        for edge in batch_extraction_result.get("edges", []):
                            # Ensure source and target have collection prefix
                            if '::' not in edge['source']:
                                edge['source'] = f"{collection_id}::{edge['source']}"
                            if '::' not in edge['target']:
                                edge['target'] = f"{collection_id}::{edge['target']}"
                            
                            edge['from_vector_record_id'] = batch_chunk_ids[0] if batch_chunk_ids else 'unknown'
                            edge['batch_chunk_ids'] = ','.join(batch_chunk_ids)
                            all_edges.append(edge)
                            
                    except Exception as e:
                        print(f"Error processing batch {batch_start//batch_size + 1}: {str(e)}")
                        errors = True
                        continue

                print(f"Completed processing batches. Total nodes: {len(all_nodes)}, Total edges: {len(all_edges)}")
                
                # Process all collected nodes
                for node in all_nodes:
                    if node['id'] == f"{collection_id}::document":
                        continue
                        
                    node_id = node['id'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    node_type = node['type'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    
                    merge_statement = f"g.mergeV([(id): '{node_id}']).option(onCreate, [(label):'{node_type}'"
                    
                    # Create a copy to avoid modifying the original
                    node_copy = node.copy()
                    del node_copy['id']
                    del node_copy['type']
                    
                    # Add node properties
                    for key, value in node_copy.items():
                        clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        clean_value = str(value).replace("\'", "\\\'")
                        merge_statement += f", '{clean_key}': '{clean_value}'"
                    
                    merge_statement += f", 'collection_id': '{collection_id}'"
                    merge_statement += '])'
                    merge_statement += '.option(onMatch, ['
                    
                    # Add onMatch properties
                    for key, value in node_copy.items():
                        clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        clean_value = str(value).replace("\'", "\\\'")
                        merge_statement += f"'{clean_key}': '{clean_value}',"
                    
                    merge_statement += f" 'collection_id': '{collection_id}'"
                    merge_statement = merge_statement.strip(',') + '])' + '\n'
                    
                    print(f"Creating node: {node_id} ({node_type})")
                    neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                    if not neptune_response:
                        print(f"Failed to create node: {node_id}")
                        errors = True
                        break

                # Process all collected edges
                for edge in all_edges:
                    edge_source = edge['source'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    edge_target = edge['target'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    edge_label = edge['edge_label'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    
                    # Create unique edge ID
                    edge_id = f"{edge_source}::{edge_label}::{edge_target}"
                    edge_id = edge_id.replace('-', '_').replace(' ', '_').replace('/', '_').replace("\'", "\\\'")
                    
                    merge_statement = f"g.mergeE([(id): '{edge_id}'])"
                    merge_statement += f".option(onCreate, [(from): '{edge_source}', (to): '{edge_target}', (T.label): '{edge_label}', weight: 1.0"
                    
                    # Add edge properties if they exist
                    edge_copy = edge.copy()
                    for key in ['source', 'target', 'edge_label']:
                        edge_copy.pop(key, None)
                    
                    for key, value in edge_copy.items():
                        clean_key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        clean_value = str(value).replace("\'", "\\\'")
                        merge_statement += f", '{clean_key}': '{clean_value}'"
                    
                    merge_statement += "])"
                    merge_statement += f".option(onMatch, [weight: 1.0])\n"
                    
                    print(f"Creating edge: {edge_source} --{edge_label}--> {edge_target}")
                    neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                    if not neptune_response:
                        print(f"Failed to create edge: {edge_id}")
                        errors = True
                        break

            # Update ingestion status based on processing results
            if errors == False:
                final_status = 'ENRICHMENT_COMPLETE'
            else:
                final_status = 'ENRICHMENT_FAILED'
            
            # For chunk-based processing, we don't update the overall document status
            # since other chunks may still be processing. The status update should be
            # handled by a separate coordination mechanism or when all chunks are done.
            if not (chunk_id and chunk_content):
                # Only update status for legacy mode (full document processing)
                final_doc_id = doc_id if doc_id.startswith(collection_id) else f"{collection_id}/{doc_id}"
                
                self.utils.set_ingestion_status(
                    user_id,
                    final_doc_id,
                    etag,
                    int(lines_processed),
                    final_status,
                    self.my_origin
                )
                
                # Update graph schema only for legacy mode
                schema_query = f"""
                    g.V()
                    .has(id, startingWith("{collection_id}"))
                    .group()
                    .by(label)
                    .by(project("node_properties", "edge_labels")
                        .by(properties().label().dedup().fold())
                        .by(outE().label().dedup().fold())
                    .dedup()
                    .fold())
                    .unfold()
                """
                print(f"Running neptune schema query {schema_query}")
                schema_response = self.utils.neptune_statement(collection_id, schema_query, 'gremlin', self.my_origin)
                print(f"Got schema response {schema_response}")
                
                if schema_response: 
                    if isinstance(schema_response, str):
                        schema_response = json.loads(schema_response)
                    body = json.loads(schema_response['body'])
                    schema_data = body["response"]["result"]["data"]["@value"]
                    schema = {}
                    for row in schema_data:
                        node_label = row['@value'][0]
                        if node_label not in schema:
                            schema[node_label] = {}
                        node_values = row['@value'][1]['@value']
                        last_value_name = ''
                        for i in range(len(node_values)):
                            node_item = node_values[i]
                            for val in node_item['@value']:
                                if isinstance(val, str):
                                    last_value_name = val
                                    if last_value_name not in schema[node_label]:
                                        schema[node_label][last_value_name] = []
                                else:
                                    for subval in val['@value']:
                                        if subval not in schema[node_label][last_value_name]:
                                            schema[node_label][last_value_name].append(subval)
                    
                    # Use the utils.upsert_graph_schema function to update the graph schema
                    schema_result = self.utils.upsert_graph_schema(
                        user_id,
                        collection_name,
                        schema,
                        origin=self.my_origin
                    )
                    
                    print(f"Updated graph schema result: {schema_result}")


def handler(event, context):
    global entity_extraction
    if not entity_extraction:
        # print(f"entity_extraction_handler received: {event}")
        entity_extraction = EntityExtraction("Entity Extraction")
    result = entity_extraction.process(event)
    print(f"entity_extraction.handler returning {result}")
    return result
