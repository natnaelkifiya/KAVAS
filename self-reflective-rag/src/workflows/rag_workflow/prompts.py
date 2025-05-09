from langchain_core.prompts import ChatPromptTemplate
from langchain import hub

REWRITER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", """You a prompt re-writer that converts an input prompt to a better version that is optimized \n 
     for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning. 
     \n DO NOT PUT IN YOUR REASONING. RETURN THE IMPROVED PROMPT YOU THINK WILL WORK NOT ANYTHIN MORE OR ANYTHIN LESS!"""),
        (
            "human",
            "Here is the initial prompt: \n\n {prompt} \n Formulate an improved prompt.",
        ),
    ]
)

GRADER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a grader assessing relevance of a retrieved document to a user prompt. \n 
    It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
    If the document contains keyword(s) or semantic meaning related to the user prompt, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the prompt."""),
        ("human", "Retrieved document: \n\n {document} \n\n User prompt: {prompt}"),
    ]
)

EXTRACTOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a prompt extractor that extracts the user prompt from a set of messages. \n 
     Look at the input and try to reason about the underlying semantic intent / meaning. \n
     DO NOT PUT IN YOUR REASONING. RETURN THE EXTRACTED PROMPT YOU THINK WILL WORK NOT ANYTHIN MORE OR ANYTHIN LESS!"""),
        (
            "human",
            "Here is the set of talks: \n\n {questions} \n Formulate an extracted prompt.",
        ),
    ]
)
RAG_PROMPT = hub.pull("rlm/rag-prompt")
