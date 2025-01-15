from .clients import AzureOpenAIClientManager, WeaviateClientManager
from .prompts.rag_promps import RAG_PROMPT, RAG_PROMPT_NEED_MORE_CONTEXT

from langgraph.graph import START, END, StateGraph
from langchain_core.documents import Document
from langchain_core.runnables.config import RunnableConfig

from pydantic import BaseModel
from typing import Optional
import logging


class GraphState(BaseModel):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        question_embedding: embedding of the question
        generation: LLM generation
        documents: list of retrieved documents
        retrieval_count: counter for retrieval attempts
    """

    question: str
    documents: Optional[list[Document]] = None
    answer: Optional[str] = None
    retrieval_count: int = 0


class GraphConfig(BaseModel):
    """
    Represents the config of our graph

    Atrributes:
        weaviate_client: the weaviate client to use
        openai_client: the openai client to use
    """

    weaviate_client: WeaviateClientManager
    openai_client: AzureOpenAIClientManager


class RAG:
    def __init__(self):
        graph = StateGraph(GraphState, config_schema=GraphConfig)

        # Add nodes
        graph.add_node("retrieve", self.retrieve)
        graph.add_node("generate", self.generate)
        
        # Add edges
        graph.add_edge(START, "retrieve")
        graph.add_conditional_edges("retrieve", self.should_retrieve_more)
        graph.add_edge("generate", END)
        
        self.graph = graph.compile()
    
    def stream(self, question: str, weaviate_client: WeaviateClientManager, openai_client: AzureOpenAIClientManager):
        config = {"configurable": {"weaviate_client": weaviate_client, "openai_client": openai_client}}
        init = {"question": question}
        for message, metadata in self.graph.stream(init, config, stream_mode="messages"):
            if metadata["langgraph_node"] == "generate":
                yield message.content
                
    def invoke(self, question: str, weaviate_client: WeaviateClientManager, openai_client: AzureOpenAIClientManager):
        config = {"configurable": {"weaviate_client": weaviate_client, "openai_client": openai_client}}
        init = {"question": question}
        result = self.graph.invoke(init, config=config)
        return result["answer"]

    def retrieve(self, state: GraphState, config: RunnableConfig):
        weaviate_client = config["configurable"].get("weaviate_client", None)
        if weaviate_client is None:
            logging.error(
                "Weaviate Client not passed to config when retrieving documents. Please modify the config when calling invoke."
            )
        collection = weaviate_client.get_client().collections.get("TEST_Document_Chunk")

        # Fetch results
        question = state.question
        response = collection.query.hybrid(
            query=question, limit=5
        )

        # Create documents
        documents = state.documents or []
        for obj in response.objects:
            documents.append(Document(page_content=obj.properties["content"]))

        return {
            "question": question,
            "documents": documents,
            "retrieval_count": state.retrieval_count + 1,
        }
        
    def generate(self, state: GraphState, config: RunnableConfig):
        openai_client = config["configurable"].get("openai_client", None)
        if openai_client is None:
            logging.error(
                "Azure OpenAI client not passed to config when generating response. Please modify the config when calling invoke."
            )
        
        documents = state.documents
        question = state.question
        
        docs_content = "\n\n".join(doc.page_content for doc in documents)
        messages = RAG_PROMPT.invoke({"question": question, "documents": docs_content})
        answer = openai_client.get_chat_client().invoke(messages)
        
        return {
            "question": question,
            "documents": documents,
            "answer": answer.content,
            "retrieval_count": state.retrieval_count
        }

    def should_retrieve_more(self, state: GraphState, config: RunnableConfig):
        logging.warning(f"Retrieval count: {state.retrieval_count}")
        logging.warning(f"Documents: {len(state.documents)}")
        if state.retrieval_count >= 3:
            return "generate"

        openai_client = config["configurable"].get("openai_client", None)
        if openai_client is None:
            logging.error(
                "Azure OpenAI client not passed to config when generating response. Please modify the config when calling invoke."
            )

        documents = state.documents
        question = state.question

        docs_content = "\n\n".join(doc.page_content for doc in documents)
        messages = RAG_PROMPT_NEED_MORE_CONTEXT.invoke({"question": question, "documents": docs_content})
        answer = openai_client.get_chat_client().invoke(messages)

        logging.warning(f"Answer: {answer.content}")

        if answer.content.strip().lower() == "yes":
            return "retrieve"
        else:
            return "generate"