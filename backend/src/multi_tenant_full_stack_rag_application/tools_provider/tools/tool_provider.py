from abc import ABC, abstractmethod, abstractstaticmethod

class ToolProvider(ABC):
    @abstractstaticmethod
    def get_inputs():
        pass

    @abstractstaticmethod
    def get_outputs():
        pass

    @abstractmethod
    def run_tool(self, **kwargs:dict):
        pass

    