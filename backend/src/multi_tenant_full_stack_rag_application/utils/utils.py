#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

sanitize_attributes = ['user_id', 'shared_by_userid', 'shared_with_userid']


def format_response(status, body, origin):
    body = sanitize_response(body)
    response = {
        'statusCode': str(status),
        'headers': {
            'Access-Control-Allow-Headers': 'Authorization, Content-Type, x-csrf-token, X-Api-Key, *',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'DELETE,OPTIONS,GET,POST,PUT',
            'Vary': 'Origin'
        },
        'body': json.dumps(body)
    }
    print(f"Returning response {response}")
    return response 


def sanitize_response(body):
    # print(f"Sanitize_response received body {body}")
    if isinstance(body, dict):
        keys = list(body.keys())
        for key in keys:
            if key in sanitize_attributes:
                # print(f"\nDeleting {key}\n")
                del body[key]
            else:
                if isinstance(body[key], dict):
                    result = sanitize_response(body[key])
                    body[key] = result
    # print(f"sanitize_response returning {body}")
    return body

