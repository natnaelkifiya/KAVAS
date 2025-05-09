from pydantic import BaseModel, Field

class InferenceOrRAG(BaseModel):
    """A binary score for the relevance check of retrieved documents"""
    
    binary_score: str = Field(
        description="The prompt requires a RAG, 'yes' or 'no'"
    )

    assistant_response: str = Field(
        description="The response provided. Empty string ('') for RAG queries, otherwise a helpful reply."
    )
