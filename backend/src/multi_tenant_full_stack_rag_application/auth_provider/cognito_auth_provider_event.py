#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from typing import Dict, Optional
from ..service_provider_event import ServiceProviderEvent

class CognitoAuthProviderEvent(ServiceProviderEvent):
    operation: str
    origin: str
    args: Dict[str, str]
    auth_token: Optional[str] = ''
    user_id: Optional[str] = ''
    account_id: Optional[str] = None
