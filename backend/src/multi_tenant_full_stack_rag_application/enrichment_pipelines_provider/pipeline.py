#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod


class Pipeline(ABC):
    def __init__(self, pipeline_name, **kwargs):
        self.pipeline_name = pipeline_name

    def get_pipeline_name(self):
        return self.pipeline_name

    @abstractmethod
    def process(self, **kwargs):
        pass
