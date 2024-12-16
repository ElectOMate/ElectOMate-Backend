from .clients import AzureOpenAIClientManager, WeaviateClientManager
from .prompts.rag_promps import RAG_PROMPT

from langgraph.graph import START, END, StateGraph
from langchain_core.documents import Document
from langchain_core.runnables.config import RunnableConfig

from pydantic import BaseModel
import logging


class GraphState(BaseModel):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        question_embedding: embedding of the question
        generation: LLM generation
        documents: list of retrieved documents
    """

    question: str
    question_embedding: list[float]
    documents: list[Document]
    answer: str


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
        graph.add_node("embed", self.embed)
        graph.add_node("retrieve", self.retrieve)
        graph.add_node("generate", self.generate)
        
        # Add edges
        graph.add_edge(START, "embed")
        graph.add_edge("embed", "retrieve")
        graph.add_edge("retrieve", "generate")
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
        result = self.graph.invoke(init, config)
        return result["answer"]

    def embed(self, state: GraphState, config: RunnableConfig):
        openai_client = config["configurable"].get("openai_client", None)
        if openai_client is None:
            logging.error(
                "Azure OpenAI client not passed to config when creating embeddings. Please modify the config when calling invoke."
            )
        azure_embedding_deployement = config["configurable"].get(
            "azure_embedding_deployement", None
        )
        if azure_embedding_deployement is None:
            logging.error(
                "Azure embedding deployement name not passed to config when creating embeddings. Please modify the config when calling invoke."
            )

        question = state["question"]
        question_embedding = openai_client.get_embedding_client().embed_query(question)
        return {"question": question, "question_embedding": question_embedding}

    def retrieve(state: GraphState, config: RunnableConfig):
        weaviate_client = config["configurable"].get("weaviate_client", None)
        if weaviate_client is None:
            logging.error(
                "Weaviate Client not passed to config when retrieving documents. Please modify the config when calling invoke."
            )
        collection = weaviate_client.get_client().collections.get("Document_Chunk")

        # Fetch results
        question = state["question"]
        question_embedding = state["question_embedding"]
        response = collection.query.hybrid(
            query=question, vector=question_embedding, limit=5
        )

        # Create documents
        documents = []
        for obj in response.objects:
            documents.append(Document(page_content=obj.properties["content"]))

        return {
            "question": question,
            "question_embedding": question_embedding,
            "documents": documents,
        }
        
    def generate(state: GraphState, config: RunnableConfig):
        openai_client = config["configurable"].get("openai_client", None)
        if openai_client is None:
            logging.error(
                "Azure OpenAI client not passed to config when creating embeddings. Please modify the config when calling invoke."
            )
        
        documents = state["documents"]
        question = state["question"]
        question_embedding = state["question_embedding"]
        
        docs_content = "\n\n".join(doc.page_content for doc in documents)
        messages = RAG_PROMPT.invoke({"question": question, "context": docs_content})
        answer = openai_client.get_chat_client().invoke(messages)
        
        return {
            "question": question,
            "question_embedding": question_embedding,
            "documents": documents,
            "answer": answer
        }