#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from .graph_store_provider import GraphStoreProvider


class GraphStoreProviderFactory:
    @staticmethod
    def get_graph_store_provider(
        py_path: str='',
        args={}
    ):
        if py_path == '':
            py_path = os.getenv('GRAPH_STORE_PROVIDER_PY_PATH', 'graph_store_provider/neptune_graph_store_provider.NeptuneGraphStoreProvider')
        parts = py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: GraphStoreProvider = provider_class(**args)
        return provider

