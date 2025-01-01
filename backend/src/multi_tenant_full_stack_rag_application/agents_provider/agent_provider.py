from abc import ABC, abstractclassmethod

class AgentProvider(ABC):
    @abstractclassmethod
    def create_agent(cls, **kwargs):
        pass

    @abstractclassmethod
    def run_agent(cls, **kwargs):
        pass
    