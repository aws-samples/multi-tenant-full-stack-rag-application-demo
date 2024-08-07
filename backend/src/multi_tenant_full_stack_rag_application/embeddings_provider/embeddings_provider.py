#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod
from enum import Enum

# some models have different prompts for search and 
# ingestion, but most don't. Default to just Ingestion 
# for ones that don't care.
EmbeddingType = Enum('EmbeddingType', ['search_document', 'search_query'])

class EmbeddingsProvider(ABC):
    
    # def get_embeddings_filter(self, top_k, similarity_threshold=0.2) -> EmbeddingsFilter:
    #     return EmbeddingsFilter(
    #         self.embeddings, 
    #         top_k,
    #         similarity_threshold=similarity_threshold
    #     )
    @abstractmethod
    def encode(self, input_text, emb_type: EmbeddingType):
        pass

    @abstractmethod
    def get_model_dimensions(self) -> int:
        pass
    
    @abstractmethod
    def get_model_max_tokens(self) -> int:
        pass

    @abstractmethod
    def get_token_count(self, input_text) -> int:
        pass

    