#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from typing import Optional, List, Dict, Any
from ..service_provider_event import ServiceProviderEvent

class BedrockProviderEvent(ServiceProviderEvent):
    # Common attributes for all operations
    operation: str
    origin: str
    args: Dict[str, Any]
    
    # model_id: Optional[str] = ''
    
    # # Operation-specific attributes
    # chunk_text: Optional[str] = ''
    # dimensions: Optional[int] = 0
    # inference_config: Optional[Dict[str, Any]] = {}
    # input_text: Optional[str] = ''
    # input_type: Optional[str] = ''
    # messages: Optional[List[Dict[str, Any]]] = []
    # prompt_id: Optional[str] = ''
    # search_text: Optional[str] = ''
