#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod
from typing import Any, Dict
from .service_provider_event import ServiceProviderEvent

class ServiceProvider(ABC):
    """
    Abstract base class for all service providers.
    
    Service providers implement the business logic for handling specific service operations.
    They receive typed ServiceProviderEvent objects and return formatted responses.
    """
    
    @abstractmethod
    def handler(self, event: ServiceProviderEvent, context: Any) -> Dict[str, Any]:
        """
        Handle the service request with a typed event object.
        
        Args:
            event: The typed service provider event containing operation, origin, and service-specific data
            context: The Lambda context or other execution context
            
        Returns:
            Dict containing the formatted response
        """
        pass
