#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from datetime import datetime
from uuid import uuid4


allowed_email_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',')


class DocumentCollection:
    def __init__(self,
        user_id: str, 
        user_email: str, 
        collection_name: str, 
        description: str, 
        vector_db_type: str='opensearch_managed', 
        collection_id: str=None,
        shared_with=[], 
        created_date: str=None, 
        updated_date: str=None, 
        *, enrichment_pipelines='', graph_schema = '',
    ):
        self.user_id = user_id
        self.user_email = user_email
        self.collection_name = collection_name
        self.description = description
        self.shared_with = self.check_allowed_email_domains(shared_with)
        self.vector_db_type = vector_db_type
        self.collection_id = collection_id if collection_id else uuid4().hex
        now = datetime.now().isoformat() + 'Z'
        self.created_date = created_date if created_date else now
        self.updated_date = updated_date if updated_date else now
        self.enrichment_pipelines = json.loads(enrichment_pipelines) if isinstance(enrichment_pipelines, str) else enrichment_pipelines
        self.graph_schema = json.loads(graph_schema) if isinstance(graph_schema, str) else graph_schema

    @staticmethod
    def check_allowed_email_domains(shared_with):
        checked_shared_with = []
        for domain in allowed_email_domains:
            print(f"Checking domain {domain} against shared_with list {shared_with}")
            if domain == '*':
                print("Shared with all domains.")
                checked_shared_with = shared_with
                break
            for email in shared_with:
                if email.endswith(domain):
                    print(f"Shared with domain {domain}, appending to results.")
                    checked_shared_with.append(email)   
                else:
                    print(f"{email} does not end with {domain}. Skipping.")
                    
        print(f"check_allowed_email_domains returning {checked_shared_with}")       
        return checked_shared_with
            
    @staticmethod
    def from_ddb_record(user, rec):
        print(f"document_collection.from_ddb_record received user {user}, and rec {rec}, type {type(rec)}")
        docs = {}
        for collection_name in rec:
            coll = rec[collection_name]['M']
            print(f"Got collection {coll}")
            shared_with = [] if 'shared_with' not in coll else coll['shared_with']['SS']
            docs[collection_name] = DocumentCollection(
                user, '', collection_name, coll['description']['S'],
                coll['vector_db_type']['S'], coll['collection_id']['S'], 
                shared_with, coll['created_date']['S'], coll['updated_date']['S'],
                enrichment_pipelines=coll['enrichment_pipelines']['S'] if 'enrichment_pipelines' in coll else '',
                graph_schema=coll['graph_schema']['S'] if 'graph_schema' in coll else '',
            )
        return docs

    def to_ddb_record(self): 
        record = {
            self.collection_name: { 'M': {
                'collection_id': {'S': self.collection_id},
                'description': {'S': self.description},
                'vector_db_type': {'S': self.vector_db_type},
                'created_date': {'S': self.created_date},
                'updated_date': {'S': self.updated_date},
                'graph_schema': {'S': str(self.graph_schema if self.graph_schema else '{}')},
                'enrichment_pipelines': {'S': str(self.enrichment_pipelines if self.enrichment_pipelines else '{}')},
            }}
        }
        if len(self.shared_with) > 0:
            record[self.collection_name]['M']['shared_with'] = {'SS': self.shared_with}

        print(f"document_collection.to_ddb_record returning {record}")
        return record

    def __dict__(self):
        return {
            'user_id': self.user_id,
            'collection_id': self.collection_id,
            'collection_name': self.collection_name,
            'description': self.description,
            'vector_db_type': self.vector_db_type,
            'created_date': self.created_date,
            'shared_with': self.shared_with,
            'updated_date': self.updated_date,
            'enrichment_pipelines': json.dumps(self.enrichment_pipelines),
            'graph_schema': json.dumps(self.graph_schema),
        }

    def __str__(self):
        return json.dumps({
            'user_id': self.user_id,
            'collection_id': self.collection_id,
            'collection_name': self.collection_name,
            'description': self.description,
            'vector_db_type': self.vector_db_type,
            'created_date': self.created_date,
            'shared_with': self.shared_with,
            'updated_date': self.updated_date,
            'enrichment_pipelines': json.dumps(self.enrichment_pipelines),
            'graph_schema': json.dumps(self.graph_schema),
        })
    
    def __eq__(self, obj):
        print(f"__eq__ got\nSELF: {self},\nOBJ:  {obj}")
        shared_with_eq = True
        if not (len(self.shared_with) == len(obj.shared_with)):
            shared_with_eq = False
        else: 
            for email in self.shared_with:
                if not email in obj.shared_with:
                    shared_with_eq = False
            print(f"Is shared_with equal? {shared_with_eq}")
        enrichment_pipelines_eq = True if self.enrichment_pipelines == obj.enrichment_pipelines else False

        graph_schema_eq = True
        if not (self.graph_schema['node_properties'] == obj.graph_schema['node_properties'] and \
            self.graph_schema['edge_labels'] == obj.graph_schema['edge_labels']):
            graph_schema_eq = False

        return shared_with_eq and \
            enrichment_pipelines_eq and \
            graph_schema_eq and \
            self.user_id == obj.user_id and \
            self.collection_id == obj.collection_id and \
            self.collection_name == obj.collection_name and \
            self.description == obj.description and \
            self.vector_db_type == obj.vector_db_type # and \
            # self.created_date == obj.created_date and \
            # self.updated_date == obj.updated_date