from typing import List, Literal
from typing_extensions import TypedDict


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        loopfix: boolean flag for loop control
    """

    question: str
    generation: str
    documents: List[str]
    scope: str
    loopfix: bool
