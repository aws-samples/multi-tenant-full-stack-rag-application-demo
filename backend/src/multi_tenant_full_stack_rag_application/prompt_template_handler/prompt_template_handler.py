#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3 
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

from .prompt_template_handler_event import PromptTemplateHandlerEvent
from .prompt_template import PromptTemplate
from multi_tenant_full_stack_rag_application import utils 

"""
GET /prompt_templates: list prompt templates to which a user has access
GET /prompt_templates/{template_id}: get a specific prompt template
POST /prompt_templates: create or update prompt template
    body = {
        'template_name': str,
        'template_text': str,
        'model_ids': [str],
        'template_id'?: str
    }
DELETE /prompt_templates/{template_id} :  delete a prompt template
"""

# use global variables to store injected dependencies on the first initialization
prompt_template_handler = None


class PromptTemplateHandler:
    def __init__(self,
        prompt_templates_table: str,
        ddb_client: boto3.client=None,
        lambda_client: boto3.client=None,
        bedrock_model_param_path:str = 'multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_model_params.json',
        prompt_template_path:str = 'multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates'
    ):
        self.utils = utils
        self.prompt_template_path = prompt_template_path
        self.prompt_templates_table = prompt_templates_table

        if not ddb_client:
            self.ddb = utils.BotoClientProvider.get_client('dynamodb')
        else: 
            self.ddb = ddb_client
        
        if not lambda_client:
            self.lambda_ = utils.BotoClientProvider.get_client('lambda')
        else:
            self.lambda_ = lambda_client
                
        self.allowed_origins = self.utils.get_allowed_origins()
        self.my_origin = self.allowed_origins['origin_prompt_template_handler']

        template_files = os.listdir(prompt_template_path)
        # # print(f"Template files in {prompt_template_path}: {template_files}")
        self.default_templates = []

        with open(bedrock_model_param_path, 'r') as f:
           self.bedrock_model_params = json.loads(f.read())

        for filename in template_files:
            # # print(f"Loading template file {filename}")
            template_name = filename.replace('.txt', '')
            model_ids = self.get_default_template_model_ids(template_name)
            # # print(f"Model ids for template {template_name} {model_ids}")
            # # print(f"Loading template file from {prompt_template_path}/{filename}")
            with open(f'{prompt_template_path}/{filename}', 'r') as f:
                new_template = PromptTemplate(
                    user_id=None,
                    user_email=None,
                    template_name=template_name,
                    template_text=f.read(),
                    model_ids=model_ids,
                    template_id=template_name,
                )
                print(f"loaded default template {new_template}")
                self.default_templates.append(new_template.__dict__())
                # # print(f"Got prompt template: {self.default_templates[template_name]}")

    @staticmethod
    def create_prompt_template_record(template_dict):
        print(f"create_prompt_template_record got {template_dict}")
        template_id = uuid4().hex if 'template_id' not in template_dict \
            else template_dict['template_id']
        created = datetime.now().isoformat() + 'Z' if 'created_date' \
            not in template_dict else template_dict['created_date']
        updated = created if 'updated_date' not in template_dict else \
            template_dict['updated_date']
        if 'stop_sequences' not in template_dict:
            template_dict['stop_sequences'] = []
        updated = created
        stop_seqs = [] if not 'stop_sequences' in template_dict else \
            template_dict['stop_sequences']
        new_template = PromptTemplate(
            template_dict['user_id'],
            template_dict['user_email'],
            template_dict['template_name'],
            template_dict['template_text'],
            template_dict['model_ids'],
            stop_seqs,
            template_id,
            created,
            updated
        )
        print(f"Returning new template {new_template}")
        return new_template
    
    def delete_prompt_template(self, user_id, template_name):
        # print(f"Deleting prompt template {template_id} for user {user_id}")
        template_id = handler_evt.template_id
        result = self.ddb.delete_item(
            TableName=self.prompt_templates_table,
            Key={
                'user_id': {'S': user_id},
                'sort_key': {'S': f"template::{template_name}"}
            },
            ConditionExpression="#template_id = :template_id",
            ExpressionAttributeNames={"#template_id": "template_id"},
            ExpressionAttributeValues={":template_id": {"S": template_id}}
        )
        # print(f"delete_prompt_template got result {result}")
        return {
            "result": "DELETED",
            "template_id": template_id,
            "template_name": template_name
        }

        # curr_templates = self.get_prompt_templates(user_id)
        # final_templates = {}
        
        # for template_name in curr_templates:
        #     template = curr_templates[template_name]
        #     if template.template_id != template_id:
        #         if hasattr(template,'stop_sequences') and \
        #             (
        #                 not isinstance(template.stop_sequences, list) or \
        #                 len(template.stop_sequences) == 0
        #             ):
        #             delattr(template,'stop_sequences')

        #         final_templates[template_name] = template
        
        # user_setting = UserSetting(
        #     user_id, 
        #     'prompt_templates', 
        #     self.templates_to_dict(final_templates)
        # )
        # # print(f"Setting data: {user_setting} ")
        # self.user_settings_provider.set_user_setting(user_setting)
        # return final_templates

    def get_default_template_model_ids(self, template_name):
        search_str = template_name.split('_')[1]
        model_ids = []
        for model_id in self.bedrock_model_params:
            if search_str in model_id:
                model_ids.append(model_id)
        return model_ids

    def get_prompt_template(self, user_id, template_id) -> PromptTemplate:
        # print(f"Getting prompt template {template_id} for user {user_id}")
        response = self.get_prompt_templates(user_id)["response"]
        print(f"get_prompt_template got response {response}")
        template = None
        for tmp in response:
            if tmp['template_id'] == template_id:
                template = tmp
                break
        print(f"Get prompt template returning {template}, type {type(template)}")
        return template

    def get_prompt_templates(self, user_id, *, limit=20, last_eval_key=''):
        print(f"Getting prompt templates for user_id {user_id}")
        if not user_id or user_id == '':
            return None

        projection_expression = "#user_id, #sort_key, " + \
          " #user_email, #template_id, #template_name, " + \
          " #template_text, #model_ids, #stop_sequences, " + \
          " #created_date, #updated_date"

        expression_attr_names = {
            "#user_id": "user_id",
            "#sort_key": "sort_key",
            "#user_email": "user_email",
            "#template_id": "template_id",
            "#template_name": "template_name",
            "#template_text": "template_text",
            "#model_ids": "model_ids",
            "#stop_sequences": "stop_sequences",
            "#created_date": "created_date",
            "#updated_date": "updated_date"
        }
        sort_key = 'template::'
        print(f"Getting all items starting with {sort_key} for user_id {user_id}")
        kwargs = {
            "TableName": self.prompt_templates_table,
            "KeyConditions": {
                "user_id": {
                    "AttributeValueList": [
                        {"S": user_id}
                    ],
                    "ComparisonOperator": "EQ"
                },
                "sort_key": {
                    "AttributeValueList": [
                        {"S": sort_key}
                    ],
                    "ComparisonOperator": "BEGINS_WITH"
                }
            },
            "ProjectionExpression": projection_expression,
            "ExpressionAttributeNames": expression_attr_names,
            "Limit": int(limit)
        }
        if last_eval_key != '':
            kwargs['ExclusiveStartKey'] = last_eval_key
        
        print(f"Querying ddb with kwargs {kwargs}")
        response = self.ddb.query(**kwargs)
        templates = []
        if "Items" in response.keys():
            for item in response["Items"]:
                prompt_template = PromptTemplate.from_ddb_record(item)
                templates.append(prompt_template.__dict__())
        print(f"Got templates {templates}, default templates {self.default_templates}")
        templates += self.default_templates
        result = {
            "response": templates,
            "last_eval_key": response.get("LastEvaluatedKey", None)
        }

        print(f"get_prompt_templates returning {result}")
        return result

    def handler(self, event, context): 
        print(f"Got event {event}")
        handler_evt = PromptTemplateHandlerEvent().from_lambda_event(event)
        method = handler_evt.method
        path = handler_evt.path

        status = 200

        if handler_evt.origin in self.allowed_origins.values() and \
            handler_evt.origin != self.allowed_origins['origin_frontend'] and \
                hasattr(handler_evt, 'prompt_template') and \
                'user_id' in handler_evt.prompt_template:
                handler_evt.user_id = handler_evt.prompt_template['user_id']
        elif handler_evt.origin not in self.allowed_origins.values():
            return self.utils.format_response(403, {'error': 'forbidden'}, None)
        
        elif hasattr(handler_evt, 'auth_token') and handler_evt.auth_token != '':
            # print(f"Getting user_id for account_id {handler_evt.account_id} and token {handler_evt.auth_token}")
            handler_evt.user_id = self.utils.get_userid_from_token(
                handler_evt.auth_token,
                self.my_origin
            )
        
        print(f"after user_id lookup, handler_evt is now {handler_evt.__dict__}")

        if method != 'OPTIONS' and handler_evt.user_id == None:
            status = 403
            result = {"error": "forbidden"}
        
        elif method == 'OPTIONS':
            result = {}

        elif method == 'GET' and path == '/prompt_templates':
            response = self.get_prompt_templates(handler_evt.user_id)
            print(f"Got response {response}")
            templates = response['response']
            if templates != []:
                result = self.templates_to_dict(templates)
            else:
                result = {}

        elif method == 'GET' and path.startswith('/prompt_templates/'):
            template_id = handler_evt.path_parameters['template_id']
            # template_id = path.split('?')[0]
            result = self.get_prompt_template(handler_evt.user_id, template_id)
            # result = self.templates_to_dict({template['template_name']: template})

        elif method == 'POST' and path == '/prompt_templates':
            body = json.loads(event['body'])
            # add the user_id to the prompt template before passing it on.
            body['prompt_template']['user_id'] = handler_evt.user_id
            body['prompt_template']['user_email'] = handler_evt.user_email
            new_template_record = self.create_prompt_template_record(body['prompt_template'])
            response = self.upsert_prompt_template(new_template_record)
            result = {
                "upserted_template_id": response,
                "upserted_template_name": new_template_record.template_name
            }

        elif method == 'DELETE' and path == ('/prompt_templates'):
            template = json.loads(event['body'])['prompt_template']
            template_name = template['template_name']
            deleted_template_id = self.delete_prompt_template(handler_evt.user_id, template_name)
            result = {
                "deleted_template_id": deleted_template_id,
                "deleted_template_name": template_name
            }

        # print(f"Returning result {result}")  
        return self.utils.format_response(status, result, handler_evt.origin)

    @staticmethod
    def templates_to_dict(templates):
        # print(f"templates_to_dict got templates {templates}")
        final_templates= {}
        for template in templates:
            if isinstance(template, PromptTemplate):
                template = template.__dict__()
            # print(f"Template is now {template}, type {type(template)}")
            template_name = template['template_name']
            if 'stop_sequences' in template and template['stop_sequences'] == []:
                del template['stop_sequences']
            final_templates[template_name] = template
        return final_templates

    def upsert_prompt_template(self, new_template: PromptTemplate):
        print(f"upsert_prompt_template got new prompt template {new_template}")
        new_template_rec = new_template.to_ddb_record()
        print(f"Got new_template_rec {new_template_rec}")
        response = self.ddb.put_item(
            TableName=self.prompt_templates_table,
            Item=new_template_rec
        )
        # print(f"upsert_prompt_template got response {response}")
        return new_template_rec['template_id']


def handler(event, context):
    global prompt_template_handler
    if not prompt_template_handler:
        prompt_templates_table = os.getenv('PROMPT_TEMPLATES_TABLE')        
        prompt_template_handler = PromptTemplateHandler(
            prompt_templates_table,
        )
    return prompt_template_handler.handler(event, context)

