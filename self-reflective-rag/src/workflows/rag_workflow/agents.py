import os
from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from workflows.rag_workflow.prompts import REWRITER_PROMPT, RAG_PROMPT, GRADER_PROMPT, EXTRACTOR_PROMPT
from workflows.rag_workflow.models import GradeAnswer, GradeHallucinations, GradeDocuments


load_dotenv(find_dotenv())

llm = ChatOpenAI(
    base_url=os.environ.get('BASE_URI'),
    api_key=os.environ.get('API_KEY'),
    model=os.environ.get('MODEL_NAME'),
    temperature=1
)

# create an llm that will rewrite the prompt/user-prompt
prompt_rewriter = REWRITER_PROMPT | llm | StrOutputParser()
query_extractor = EXTRACTOR_PROMPT | llm | StrOutputParser()

# create an llm that will grade the documents
structured_document_grader = llm.with_structured_output(GradeDocuments)
document_grader = GRADER_PROMPT | structured_document_grader 

# create an llm that will produce the final rag answer
answer_generator = RAG_PROMPT | llm | StrOutputParser()

