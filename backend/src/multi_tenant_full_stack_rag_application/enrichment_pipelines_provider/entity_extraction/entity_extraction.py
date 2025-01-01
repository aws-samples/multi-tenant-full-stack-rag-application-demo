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
            ddb_rec = record['dynamodb']
            if not (record['eventName'] == 'MODIFY' and \
                ddb_rec['NewImage']['progress_status']['S'] == 'AWAITING_ENRICHMENT'):
                print(f"Skipping ddb_rec because it's not the right progress status: {ddb_rec}")
                continue
            
            new_image = ddb_rec['NewImage']
            print(f"Got new image {new_image}")
            collection_id = new_image['doc_id']['S'].split('/')[0]
            account_id = record['eventSourceARN'].split(':')[4]
            user_id = new_image['user_id']['S']

            response = self.utils.get_document_collections(user_id, collection_id, origin=self.my_origin)
            print(f"Got response {response}")
            enrichment_pipelines = {}
            collection_name = list(response.keys())[0]
            collection = response[collection_name]
            if collection and 'enrichment_pipelines' in collection:
                print(f"Got collection {collection}")
                enrichment_pipelines = json.loads(collection['enrichment_pipelines'])
            print(f"enrichment pipelines is now {enrichment_pipelines}")
            if not ('entity_extraction' in enrichment_pipelines and enrichment_pipelines['entity_extraction']['enabled'] == True):
                print(f"Skipping entity extraction for doc collection {collection} because it doesn't have entity extraction enabled.")
                return None
            # now fetch all the text chunks from this doc in the vector
            # database
            query = {
                "query": {
                    "term": {
                        "metadata.source.keyword": new_image['doc_id']['S']
                    }
                }
            }
            response = self.utils.vector_store_query(
                collection_id,
                query,
                self.my_origin
            )
            print(f"response frm vector_store_query was {response}")
            body = json.loads(response['body'])
            print(f"Got chunks for for entity extraction {body}")
            doc_text = ''
            for hit in body['hits']['hits']:
                doc_text += hit['_source']['content']
            print(f"Got doc text\n{doc_text}")
            # # get the document collection by collection_id
            # doc_collection = self.utils.get_document_collections(
            #     user_id, collection_id
            # )
            # print(f"Got doc_collection {doc_collection}")
            # if not ('entity_extraction' in collection.enrichment_pipelines and \
            #     collection.enrichment_pipelines['entity_extraction']['enabled']) :
            #     # print(f"Skipping entity extraction for doc collection {doc_collection} because it doesn't have entity extraction enabled.")
            #     new_image['progress_status']['S'] = 'ENRICHMENT_DISABLED_SKIPPING'
            #     if not new_image['doc_id']['S'].startswith(collection_id):
            #         new_image['doc_id']['S'] = f"{collection_id}/{new_image['doc_id']['S']}"
            #     self.ingestion_status_provider.set_ingestion_status(ing_status)
            #     return True

            print(f"Entity extraction is enabled for collection {collection_id}")
            print(f"Collection: {collection}, type {type(collection)}")
            template_id = json.loads(collection['enrichment_pipelines'])["entity_extraction"]["templateIdSelected"]
            response = self.utils.get_prompt_template(
                template_id,
                user_id,
                self.my_origin
            )
            print (f"Got response {response}, type {type(response)}")
            body = json.loads(response['body'])
            template = body[list(body.keys())[0]]
            print(f"Got template {template}, type ({type(template)}")
            ee_template_name = template['template_name']  #  ['template_name']
            ee_template_text = template['template_text']  #  ['template_text']   
            graph_schema = collection['graph_schema']

            prompt = ee_template_text.replace('{context}', doc_text).replace('{graph_schema}', collection['graph_schema'])
            prompt = f"<FILENAME>{new_image['doc_id']['S']}</FILENAME>\n\n" + prompt
            msgs = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            response = self.utils.invoke_bedrock(
                'invoke_model',
                {
                    "modelId": self.model_id,
                    "messages": msgs,
                    "inferenceConfig": {
                        "maxTokens": 2000,
                        "temperature": 0.0,
                        "stopSequences": ["</JSON>"] if 'stop_sequences' not in template else template['stop_sequences']
                    }
                },
                self.my_origin
            )
            print(f"Bedrock response {response}, type {type(response)}")
            response_str = response['response'].replace('\n', '').replace("\n", "").replace('<JSON>', '').replace('</JSON>', '').strip()
            print(f"Before json parsing, response_str = '\n{response_str}\n'")
            response = json.loads(response_str)
            print(f"Got node and entity results {response}")
            gremlin_statements = ''
            ids_to_types = {}
            errors = False
            document_id = new_image['doc_id']['S'].replace('/', '::', 1).replace('-', '_')
            response['nodes'].append(
                {
                    "id": document_id,
                    "type": "document",
                    "source": new_image['doc_id']['S']
                }
            )
            
            for node in response["nodes"]:
                if node['id'] == f"{collection_id}::document":
                    continue
                if '::' not in node['id']:
                    node['id'] = f"{collection_id}::{node['id']}"

                response['edges'].append({
                    "source": document_id,
                    "edge_label": "contains",
                    "target": node['id'],
                })
                node_id = node['id'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                node_type = node['type'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                ids_to_types[node_id] = node_type
                merge_statement = f"g.mergeV([(id): '{node_id}']).option(onCreate, [(label):'{node_type}'"
                # gremlin_statements += f".mergeV([(id):{node['id']}]).option(onCreate, [(label):'{node['type']}']).as('{node['id']}').property(id, '{node['id']}')"
                del node['id']
                del node['type']
                keys = node.keys()
                for key in keys:
                    key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    node[key] = node[key].replace("\'", "\\\'")
                    merge_statement += f", '{key}': '{node[key]}'"
                merge_statement += f", 'from_file': '{new_image['doc_id']['S']}'"
                merge_statement += f", 'collection_id': '{collection_id}'"
                merge_statement += '])'
                merge_statement += '.option(onMatch, ['
                for key in keys:
                    key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                    # node[key] = node[key].replace("\'", "\\\'")
                    merge_statement += f"'{key}': '{node[key]}',"
                merge_statement += f" 'from_file': '{new_image['doc_id']['S']}'"
                merge_statement += f", 'collection_id': '{collection_id}'"
                merge_statement = merge_statement.strip(',') + '])' + '\n'
                gremlin_statements += merge_statement
                # print(f"Running gremlin statement {merge_statement}") 
                neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                print(f"Neptune response {neptune_response}")
                if not neptune_response:
                    errors = True
                    break

            for edge in response["edges"]:
                merge_statement = ''
                edge['source'] = edge['source'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                if '::' not in edge['source']:
                    edge['source'] = f"{collection_id}::{edge['source']}"

                edge['target'] = edge['target'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                if '::' not in edge['target']:
                    edge['target'] = f"{collection_id}::{edge['target']}"
                
                edge['edge_label'] = edge['edge_label'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                edge_id = f"{new_image['doc_id']['S']}::{edge['source'].split('::')[1]}::{edge['edge_label']}::{edge['target'].split('::')[1]}"
                edge_id = edge_id.replace('-', '_').replace(' ', '_').replace('/', '_').replace("\'", "\\\'")
                merge_statement += f"g.mergeE([(id): '{edge_id}'])"
                merge_statement += f".option(onCreate, [(from): '{edge['source']}', (to): '{edge['target']}', (T.label): '{edge['edge_label']}', weight: 1.0])"
                merge_statement += f".option(onMatch, [weight: 1.0])\n"
                gremlin_statements += merge_statement
                # print(f"Running gremlin statement {merge_statement}")
                neptune_response = self.utils.neptune_statement(collection_id, merge_statement, 'gremlin', self.my_origin)
                print(f"Neptune response {neptune_response}")
                if not neptune_response:
                    errors = True
                    break
                # neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', 'gremlin', merge_statement)
                # # print(f"Got neptune response {neptune_response}")
                # if isinstance(neptune_response, str):
                #     neptune_response = json.loads(neptune_response)
                # if not ('status' in neptune_response and \
                # 'code' in neptune_response['status'] and \
                # neptune_response['status']['code'] == 200):
                #     errors = True
                #     break
            # # print(f"About to run gremlin statements {json.dumps(gremlin_statements)}")
            # neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', 'gremlin', gremlin_statements)
            # # print(f"Got neptune response {neptune_response}")
            # if isinstance(neptune_response, str):
            #     neptune_response = json.loads(neptune_response)

            if errors == False:
                new_image['progress_status']['S'] = 'ENRICHMENT_COMPLETE'

            else:
                new_image['progress_status']['S'] = 'ENRICHMENT_FAILED'
                # raise Exception(f"Error processing {new_image['doc_id']['S']}")
            if not new_image['doc_id']['S'].startswith(collection_id):
                new_image['doc_id']['S'] = f"{collection_id}/{new_image['doc_id']['S']}"
            self.utils.set_ingestion_status(
                new_image['user_id']['S'],
                new_image['doc_id']['S'],
                new_image['etag']['S'],
                new_image['lines_processed']['N'],
                new_image['progress_status']['S'],
                self.my_origin
            )
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
            neptune_schema = {}
            if schema_response: 
                if isinstance(schema_response, str):
                    schema_response = json.loads(schema_response)
                print(f"Got neptune node_types response {schema_response}")
                body = json.loads(schema_response['body'])
                schema_data = body["response"]["result"]["data"]["@value"]
                schema = {}
                for row in schema_data:
                    print(f"schema response row {row}")
                    node_label = row['@value'][0]
                    if node_label not in schema:
                        schema[node_label] = {}
                    node_values = row['@value'][1]['@value']
                    print(f"{node_label} has node_values {node_values}")
                    last_value_name = ''
                    for i in range(len(node_values)):
                        node_item = node_values[i]
                        print(f"{node_label} has node_item {node_item}")
                        for val in node_item['@value']:
                            print(f"Got @value {val}")
                            if isinstance(val, str):
                                last_value_name = val
                                print(f"Set last_value_name to {last_value_name}")
                                if last_value_name not in schema[node_label]:
                                    schema[node_label][last_value_name] = []
                            else:
                                for subval in val['@value']:
                                    print(f"Got @value {subval}")
                                    print(f"schema is now {schema}")
                                    if subval not in schema[node_label][last_value_name]:
                                        schema[node_label][last_value_name].append(subval)
                print(f"Got schema: {schema}")
                collection['graph_schema'] = schema
                collection['user_id'] = user_id
                print(f"updating doc collection with schema: {collection}")
                collection_save_result = self.utils.upsert_doc_collection(collection, self.my_origin)
                print(f"Updated collections result {collection_save_result}")

def handler(event, context):
    global entity_extraction
    if not entity_extraction:
        # print(f"entity_extraction_handler received: {event}")
        entity_extraction = EntityExtraction("Entity Extraction")
    result = entity_extraction.process(event)
    print(f"entity_extraction.handler returning {result}")
    return result
