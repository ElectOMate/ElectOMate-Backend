from langgraph.graph import START, END, StateGraph

from .edges.decide_to_generate import decide_to_generate
from .edges.grade_generation_v_documents_and_question import grade_generation_v_documents_and_question
from .edges.handle_generic_response import handle_generic_response
from .edges.route_edges import route_question
from .graph_state import GraphState
from .nodes.generate import generate
from .nodes.generate2 import generate2
from .nodes.grade_documents import grade_documents
from .nodes.retrieve import retrieve
from .nodes.embed import embed
from .nodes.transform_query import transform_query


def get_graph():
    if not hasattr(get_graph, 'app'):
        workflow = StateGraph(GraphState)

        # Define the nodes
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("generate", generate)
        workflow.add_node("generate2", generate2)
        workflow.add_node("embed", embed)
        workflow.add_node("transform_query", transform_query)
        workflow.add_node("handle_generic_response", handle_generic_response)  # New node

        # Build graph
        workflow.add_conditional_edges(
            START,
            route_question,
            {
                "needs_context": "embed",
                "generic": "handle_generic_response",
                "end": END,
            },
        )
        workflow.add_edge("embed", "retrieve")

        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_edge("handle_generic_response", END)  # Direct path to end for generic responses
        workflow.add_conditional_edges(
            "grade_documents",
            decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )

        # Initialize a counter variable
        transform_query_counter = 0

        # Add conditional edges using the counter
        workflow.add_conditional_edges(
            "transform_query",
            check_transform_query,
            {
                "generate2": "generate2",
                "retrieve": "embed"
            }
        )

        workflow.add_conditional_edges(
            "generate",
            grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": END,
                "not useful": "transform_query",
            },
        )
        workflow.add_edge("generate2", END)

        # Compile
        get_graph.app = workflow.compile()

    return get_graph.app


def check_transform_query(state):
    if not 'loops' in state:
        state['loops'] = 0
    if state['loops'] >= 3:
        return "generate2"
    else:
        state['loops'] += 1
        return "retrieve"
