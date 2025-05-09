from workflows.master.states import MasterState

def route_rag_output(state: MasterState) -> str:
    """
    Route the output of the RAG process to the appropriate next step.

    Args:
        state (MasterState): The current state of the workflow.

    Returns:
        str: The name of the
    """
    print('---DECIDING ROUTE---')
    needs_rag = state['needs_rag']
    
    if needs_rag == "yes":
        print("---RAG: YES---")
        return "rag_generation"
    else:
        print("---RAG: NO---")
        return "final_response".e5gvh6