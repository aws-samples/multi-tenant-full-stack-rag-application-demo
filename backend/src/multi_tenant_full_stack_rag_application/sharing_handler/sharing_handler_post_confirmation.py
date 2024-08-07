#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class SharingHandlerPostConfirmationEvent:
    def from_lambda_event(self, event):
        # self.account_id = event['requestContext']['accountId']
        # [self.method, self.path] = event['routeKey'].split(' ')
        # if 'headers' in event:
        #     if 'authorization' in event['headers']:
        #         self.auth_token = event['headers']['authorization'].split(' ', 1)[1]
        #     if 'origin' in event['headers']:
        #         self.origin = event['headers']['origin']
        # if 'pathParameters' in event and \
        #     'user_prefix' in event['pathParameters']:
        #     self.user_prefix = event['pathParameters']['user_prefix']

        return self
