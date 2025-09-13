#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from pydantic import BaseModel
from abc import ABC

class ServiceProviderEvent(BaseModel, ABC):
    """
    Abstract base class for all service provider events.
    
    All service provider events must have:
    - operation: The specific operation to perform
    - origin: The origin of the caller (frontend origin or Lambda function name)
    
    Subclasses should add their service-specific attributes.
    """
    operation: str
    origin: str
