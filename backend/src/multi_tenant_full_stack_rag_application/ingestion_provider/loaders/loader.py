#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# import joblib
import os

from abc import ABC, abstractmethod
from datetime import datetime

from multi_tenant_full_stack_rag_application.ingestion_provider.splitters.optimized_paragraph_splitter import OptimizedParagraphSplitter

class Loader(ABC):
    def __init__(self, **kwargs):
        print("Initialized Loader")

    @abstractmethod
    def load(self, path):
        pass

    @abstractmethod
    def load_and_split(self, path, user_id, source, *, extra_metadata={}, extra_header_text='', one_doc_per_line=False, return_dicts=False):
        pass
