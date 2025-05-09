import os
from dotenv import load_dotenv, find_dotenv
from workflows.rag_workflow.nodes import generate_response, retrieve_documents, grade_documents, transform_query
from workflows.rag_workflow.edges import decide_to_generate
from workflows.rag_workflow.agents import document_grader, prompt_rewriter, answer_generator
from workflows.rag_workflow.states import RAGState, InputState, OutputState
from scripts.embedding_service import PineconeEmbeddingManager
from langgraph.graph import START, END, StateGraph


# load environment variables
load_dotenv(find_dotenv())
api_key = os.environ.get('PINECONE_API_KEY')
index_name = os.environ.get('INDEX_NAME')
name_space = os.environ.get('NAMESPACE')

# instantiate the Pinecone Manager
manager = PineconeEmbeddingManager(api_key=api_key, index_name='kifiya', name_space='test')

# define the graph nodes
retriever = lambda state: retrieve_documents(state=state, retriever=manager)    
grader = lambda state: grade_documents(state=state, document_grader=document_grader)
rewriter = lambda state: transform_query(state=state, prompt_rewriter=prompt_rewriter)
generator = lambda state: generate_response(state=state, answer_generator=answer_generator)

# create a workflow/graph
rag_workflow = StateGraph(RAGState, input=InputState, output=OutputState)

# register the nodes to the rag_workflow/graph
rag_workflow.add_node("retrieve", retriever)
rag_workflow.add_node("rewriter", rewriter)
rag_workflow.add_node("grade_documents", grader)
rag_workflow.add_node("answer_generator", generator)

# add edges
rag_workflow.add_edge(START, "retrieve")
rag_workflow.add_edge("retrieve", "grade_documents")
rag_workflow.add_edge("rewriter", "retrieve")
rag_workflow.add_edge("answer_generator", END)


# add conditional edges
rag_workflow.add_conditional_edges(source="grade_documents", path=decide_to_generate)
