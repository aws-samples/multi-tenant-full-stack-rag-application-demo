#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from abc import ABC, abstractmethod

class ToolProviderEvent(ABC):
    def __init__(self,
        operation: str='',
        *args
    ):
        self.operation = operation

    @abstractmethod
    def from_lambda_event(self, evt):
        pass

    

