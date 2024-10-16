#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod

class GraphStoreProvider(ABC):
    @abstractmethod
    def execute_statement(self, collection_id, statement, statement_type='gremlin'):
        pass