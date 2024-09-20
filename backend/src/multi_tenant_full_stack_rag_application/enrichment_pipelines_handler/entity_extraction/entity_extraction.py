#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# EntityExtraction watches for changes in the ingestion status
# table. If a record status changes to INGESTED, it checks
# the collection ID to see if it has the entity extraction
# enrichment pipeline enabled. If it does, it performs
# entity extraction and sets the entity extraction status to
# ENRICHMENT_COMPLETE. If it fails, it sets the status to
# ENRICHMENT_FAILED. If the collection doesn't have the entity
# extraction enrichment pipeline enabled, it does nothing.

import base64
import boto3
import json
import os
import shutil

from aws_kinesis_agg.deaggregator import deaggregate_records
from base64 import b64encode
from uuid import uuid4

import multi_tenant_full_stack_rag_application.enrichment_pipelines_provider.entity_extraction.neptune_client as neptune

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from multi_tenant_full_stack_rag_application.enrichment_pipelines import Pipeline


default_entity_extraction_template_path = 'multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/default_entity_extraction_template.txt'
default_extraction_model_id = os.getenv('EXTRACTION_MODEL_ID')


class EntityExtraction(Pipeline):
    def __init__(self, 
        pipeline_name: str, 
        *,
        extraction_prompt_template_id: str=None,
        neptune_endpoint: str=None,
        # pdf_loader: Loader=None,
        # s3_client: boto3.client=None,
        # splitter: Splitter=None,
        **kwargs
    ):
        super().__init__(pipeline_name, **kwargs)

        if not neptune_endpoint:
            self.neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT')
        else:
            self.neptune_endpoint = neptune_endpoint

        # if not extraction_prompt_template_id:
        # with open(default_entity_extraction_template_path, 'r') as f_in:
        #     self.entity_extraction_template_text = f_in.read()

    @staticmethod
    def decode_payload(enc_payload):
        return base64.b64decode(enc_payload).strip()
   
    def neptune_query(self, statement):
        print(f"Running neptune query {statement}")
        neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', 'gremlin', statement)
        print(f"Got neptune response {neptune_response}")
        if isinstance(neptune_response, str):
            neptune_response = json.loads(neptune_response)
        if 'status' in neptune_response and \
        'code' in neptune_response['status'] and \
        neptune_response['status']['code'] == 200:
            return neptune_response
        else:
            print(f"Error processing gremlin statement {statement}")
            return False

    def process(self, event):
        print(f"entity_extraction.process received {event}")
        records = deaggregate_records(event['Records'])
        for record in records:
            print(f"Got record {record}")
            enc_payload = record["kinesis"]["data"]
            payload = self.decode_payload(enc_payload)
            rec = json.loads(payload)
            print(f"Decoded payload: {rec}, {rec.keys()}")
            ddb_rec = rec["dynamodb"]
            print(f"Got ddb_rec {ddb_rec}")
       
            if 'NewImage' in ddb_rec and \
            rec["eventName"] == 'MODIFY':
                ing_status = IngestionStatus.from_ddb_record(ddb_rec['NewImage'])
                if ing_status.progress_status in ['INGESTED', 'ENRICHMENT_FAILED']:
                    collection_id = ing_status.doc_id.split('/')[0]
                    account_id = record['eventSourceARN'].split(':')[4]
                    user_id = ddb_rec['NewImage']['user_id']['S']

                    print(f"Searching for user_id {user_id}, collection_id {collection_id}, {account_id}")
                    dch_evt = {
                        'account_id': account_id,
                        'collection_id': collection_id,
                        'method': 'GET',
                        'path': f'/document_collections/{collection_id}/edit',
                        'user_email': '',
                        'user_id': user_id,
                        'origin': 'KINESIS'
                    }
                    print(f"Got dch_evt dict {dch_evt}")
                    dch_evt = DocumentCollectionsHandlerEvent(**dch_evt)
                    print(f"created dch_evt {dch_evt}")
                    collection = self.document_collections_handler.get_doc_collection(user_id, collection_id, include_shared=False)
                    print(f"Got collection {collection}")
                    if not collection or 'entity_extraction' not in collection.enrichment_pipelines:
                        return None
                    # now fetch all the text chunks from this doc in the vector
                    # database
                    query = {
                        "query": {
                            "term": {
                                "metadata.source.keyword":  ing_status.doc_id
                            }
                        }
                    }
                    response = self.vector_store_provider.query(
                        collection_id,
                        query
                    )
                    # print(f"Got chunks for for entity extraction {response}")
                    doc_text = ''
                    for hit in response['hits']['hits']:
                        doc_text += hit['_source']['content']
                    
                    # get the document collection by collection_id
                    doc_collection = self.document_collections_handler.get_doc_collection(
                        user_id,
                        collection_id
                    )
                    print(f"Got doc_collection {doc_collection}")
                    if not ('entity_extraction' in doc_collection.enrichment_pipelines and \
                        doc_collection.enrichment_pipelines['entity_extraction']['enabled']) :
                        print(f"Skipping entity extraction for doc collection {doc_collection} because it doesn't have entity extraction enabled.")
                        ing_status.progress_status = 'ENRICHMENT_DISABLED_SKIPPING'
                        if not ing_status.doc_id.startswith(collection_id):
                            ing_status.doc_id = f"{collection_id}/{ing_status.doc_id}"
                        self.ingestion_status_provider.set_ingestion_status(ing_status)
                        return True

                    print(f"Entity extraction is enabled for collection {collection_id}")
                    entity_extraction_template = self.prompt_template_handler.get_prompt_template(
                        user_id,
                        doc_collection.enrichment_pipelines['entity_extraction']['templateIdSelected']
                    )
                    print (f"Got entity_extraction_template {entity_extraction_template}")
                    ee_template_name = entity_extraction_template.template_name  #  ['template_name']
                    ee_template_text = entity_extraction_template.template_text  #  ['template_text']    
                    prompt = ee_template_text.replace('{document_content}', doc_text)
                    prompt = f"<COLLECTION_ID>\n{collection_id}\n</COLLECTION_ID>\n<FILENAME>{ing_status.doc_id}</FILENAME>\n\n" + prompt
                    response = self.bedrock.invoke_model(
                        default_extraction_model_id,
                        prompt,
                        messages=[{
                            "mime_type": "text/plain",
                            "content": prompt
                        }],
                        model_kwargs={
                            "max_tokens": 4096,
                            "temperature": 0.0,
                            "top_p": 0.9,
                            "top_k": 250,
                            "stop_sequences": ["</json>"]
                        }
                    )
                    print(f"Bedrock response {response}, type {type(response)}")
                    response_json_str = response.replace('<JSON>', '').replace('</JSON>', '').replace("\n", "")
                    print(f"Got response_json_str {response_json_str}")
                    response = json.loads(response_json_str)
                    print(f"Got node and entity results {response}")
                    gremlin_statements = ''
                    ids_to_types = {}
                    errors = False
                    document_id = ing_status.doc_id.replace('/', '::').replace('-', '_')
                    response['nodes'].append(
                        {
                            "id": document_id,
                            "type": "document",
                            "source": ing_status.doc_id
                        }
                    )
                    
                    for node in response["nodes"]:
                        if node['id'] == f"{collection_id}::document":
                            continue
                        
                        response['edges'].append({
                            "source": document_id,
                            "target": node['id'],
                            "type": "contains"
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
                        merge_statement += f", 'from_file': '{ing_status.doc_id}'"
                        merge_statement += f", 'collection_id': '{collection_id}'"
                        merge_statement += '])'
                        merge_statement += '.option(onMatch, ['
                        for key in keys:
                            key = key.replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                            # node[key] = node[key].replace("\'", "\\\'")
                            merge_statement += f"'{key}': '{node[key]}',"
                        merge_statement += f" 'from_file': '{ing_status.doc_id}'"
                        merge_statement += f", 'collection_id': '{collection_id}'"
                        merge_statement = merge_statement.strip(',') + '])' + '\n'
                        gremlin_statements += merge_statement
                        print(f"Running gremlin statement {merge_statement}")
                        neptune_response = self.neptune_query(merge_statement)
                        if not neptune_response:
                            errors = True
                            break
                    for edge in response["edges"]:
                        merge_statement = ''
                        edge['source'] = edge['source'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        edge['target'] = edge['target'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        edge['type'] = edge['type'].replace('-', '_').replace(' ', '_').replace("\'", "\\\'")
                        edge_id = f"{ing_status.doc_id}::{edge['source'].split('::')[1]}::{edge['type']}::{edge['target'].split('::')[1]}"
                        edge_id = edge_id.replace('-', '_').replace(' ', '_').replace('/', '_').replace("\'", "\\\'")
                        merge_statement += f"g.mergeE([(id): '{edge_id}'])"
                        merge_statement += f".option(onCreate, [(from): '{edge['source']}', (to): '{edge['target']}', (T.label): '{edge['type']}', weight: 1.0])"
                        merge_statement += f".option(onMatch, [weight: 1.0])\n"
                        gremlin_statements += merge_statement
                        print(f"Running gremlin statement {merge_statement}")
                        neptune_response = self.neptune_query(merge_statement)
                        if not neptune_response:
                            errors = True
                            break
                        # neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', 'gremlin', merge_statement)
                        # print(f"Got neptune response {neptune_response}")
                        # if isinstance(neptune_response, str):
                        #     neptune_response = json.loads(neptune_response)
                        # if not ('status' in neptune_response and \
                        # 'code' in neptune_response['status'] and \
                        # neptune_response['status']['code'] == 200):
                        #     errors = True
                        #     break
                    # print(f"About to run gremlin statements {json.dumps(gremlin_statements)}")
                    # neptune_response = neptune.make_signed_request(self.neptune_endpoint, 'POST', 'gremlin', gremlin_statements)
                    # print(f"Got neptune response {neptune_response}")
                    # if isinstance(neptune_response, str):
                    #     neptune_response = json.loads(neptune_response)

                    if errors == False:
                        ing_status.progress_status = 'ENRICHMENT_COMPLETE'
                        print()
                        if not ing_status.doc_id.startswith(collection_id):
                            ing_status.doc_id = f"{collection_id}/{ing_status.doc_id}"
                        self.ingestion_status_provider.set_ingestion_status(ing_status)
                    else:
                        ing_status.progress_status = 'ENRICHMENT_FAILED'
                        self.ingestion_status_provider.set_ingestion_status(ing_status)
                        raise Exception(f"Error processing {ing_status.doc_id}")
                    
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
                    schema_response = self.neptune_query(schema_query)
                    neptune_schema = {}
                    if schema_response: 
                        if isinstance(schema_response, str):
                            schema_response = json.loads(schema_response)
                        print(f"Got neptune node_types response {schema_response}")
                        schema_data = schema_response["result"]["data"]["@value"]
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
                        collection.graph_schema = schema
                        collection_save_result = self.document_collections_handler.upsert_doc_collection(collection, dch_evt)
                        print(f"Updated collections result {collection_save_result}")

def handler(event, context):
    global kinesis
    print(f"entity_extraction_handler received: {event}")
    e = EntityExtraction("Entity Extraction")
    result = e.process(event)
    print(f"entity_extraction.handler returning {result}")
    return result
