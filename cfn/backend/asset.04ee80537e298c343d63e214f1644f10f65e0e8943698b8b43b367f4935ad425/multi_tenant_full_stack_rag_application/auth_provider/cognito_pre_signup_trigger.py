#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import os

allowed_email_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',')


def handler(event, context):
    allowed = False
    email = event['request']['userAttributes']['email']
    user_email_domain = email.split('@')[1]
    for domain in allowed_email_domains:
        domain = domain.strip()
        if domain == '*' or domain == user_email_domain:
            allowed = True
            break
    if not allowed:
        raise Exception(f"Domain {user_email_domain} is not configured as an allowed email domain")
    # Return to Amazon Cognito
    return event