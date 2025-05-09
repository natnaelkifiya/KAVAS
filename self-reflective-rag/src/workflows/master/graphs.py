import os
from dotenv import load_dotenv, find_dotenv
from langgraph.graph import START, END, StateGraph
from workflows.master.nodes import inference_or_rag, generate_response
from workflows.master.agents import rag_decider, assistant
from workflows.master.states import MasterState, InputState, OutputState

load_dotenv(find_dotenv())

# define the graph nodes
inference = lambda state: inference_or_rag(state=state, master=rag_decider)
final_answer_generator = lambda state: generate_response(state=state, answer_generator=assistant)

# create a workflow/graph
master_workflow = StateGraph(MasterState, input=InputState, output=OutputState)

# register the nodes to the workflow/graph
master_workflow.add_node("inference", inference)
master_workflow.add_node("final_answer_generator", final_answer_generator)

# add edges
master_workflow.add_edge(START, "inference")
master_workflow.add_edge("inference", "final_answer_generator")
master_workflow.add_edge("final_answer_generator", END)

if __name__ == "__main__":
    app = master_workflow.compile()
    app.invoke({
        "prompt": "What is the capital of France?",
        "conversation_history": [
            {
                "role": "user",
                "content": "What is the capital of France?"
            }
        ]
    })