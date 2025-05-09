from langchain_openai import ChatOpenAI
from workflows.master.states import InputState, OutputState, MasterState
from langgraph.checkpoint.memory import MemorySaver

# temp memory checkpointer
memory = MemorySaver()


# import and set up the RAG workflow
from workflows.rag_workflow.graphs import rag_workflow

rag_generator = rag_workflow.compile(checkpointer=memory)

def inference_or_rag(state: InputState, master: ChatOpenAI) -> any:
    print('---INFERENCE OR RAG---')
    prompt = state['prompt']
    conversation_history = "\n".join(state["conversation_history"])

    result = master.invoke({
        "prompt": prompt,
        "conversation_history": conversation_history
    })

    print("Needs RAG: ",result.binary_score)

    return {
        "needs_rag": result.binary_score,
        "assistant_response": result.assistant_response,
        "prompt": prompt,
        "conversation_history": conversation_history
    }

def generate_response(state: MasterState, answer_generator: ChatOpenAI) -> OutputState:
    print('---GENERATING RESPONSE---')
    history = state["conversation_history"]
    prompt = state['prompt']
    needs_rag = state['needs_rag']
    result = None

    if needs_rag.lower() == "yes":
        print("---Quering the RAG---")
        # query the rag
        rag_generation = rag_generator.invoke({
            "prompt": prompt,
        })

        # use the answer generator to obtain a proper response
        result = answer_generator.invoke({
            "generation": rag_generation,
            "conversation_history": history,
            "prompt": prompt
        })
        
        return {
        "generation": result
        }

    elif needs_rag.lower() == "no":
        print("---No RAG needed---")
        return {
            "generation": state['assistant_response']
        }