#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod

class GraphStoreProvider(ABC):
    @abstractmethod
    def execute_query(self, collection_id):
        pass