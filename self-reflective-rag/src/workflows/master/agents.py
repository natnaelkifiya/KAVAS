import os
from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from workflows.master.prompts import MASTER_PROMPT, FINAL_ANSWER_PROMPT
from workflows.master.models import InferenceOrRAG

load_dotenv(find_dotenv())

llm = ChatOpenAI(
    base_url=os.environ.get('BASE_URI'),
    api_key=os.environ.get('API_KEY'),
    model=os.environ.get('MODEL_NAME'),
    temperature=1
)


# create an llm that will decide if the prompt needs RAG or not and gives a response accordingly
structured_rag_decider = llm.with_structured_output(InferenceOrRAG)
rag_decider = MASTER_PROMPT | structured_rag_decider

# create an llm that will provide the final answer but has a persona of the KAVAS assistant
assistant = FINAL_ANSWER_PROMPT | llm | StrOutputParser()