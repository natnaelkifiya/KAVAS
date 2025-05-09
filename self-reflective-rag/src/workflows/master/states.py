from typing import List, Optional
from typing_extensions import TypedDict

class InputState(TypedDict):
    """
    Represents the state of the input sent by the user graph.

    Attributes:
        user_id: the user id 
        conversation_history: the previous conversations of the user
        prompt: question
    """
    user_id: Optional[str]
    conversation_history: Optional[List[str]]
    prompt: str

class IntermediateState(TypedDict):
    """
    Represents the intermediate state during processing.
    
    Attributes:
        rag_generation: the LLM generated response for RAG
        needs_rag: whether the LLM thinks it needs RAG or not
        assistant_response: the LLM generated response for the assistant
    """
    needs_rag: str
    assistant_response: str
    rag_generation: str

class OutputState(TypedDict):
    """
    Represents the state of the output sent by the workflow.

    Attributes:
        generation: the LLM generated response
    """
    generation: str

class MasterState(InputState, IntermediateState, OutputState):
    """
    Represents the state of our graph.
    """
    pass