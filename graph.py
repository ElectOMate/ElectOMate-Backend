import logging

import dotenv
from langchain_core.runnables import RunnableConfig


from graph.graph_state import GraphState
from .graph.graph_config import get_graph

# Initialize the state with loopfix set to False
initial_state = GraphState(
    question="",
    generation="",
    documents=[],
    scope="",
    loopfix=False
)

if __name__ == "__main__":
    dotenv.load_dotenv()
    app = get_graph()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    config = RunnableConfig(recursion_limit=10)
    preamble = """Our algorithm has reach our self-imposed recursion limit of 10. 
    This means that we are not confident enough that the data in the context is enough to answer your question. 
    However, we will still provide the best answer we can given the data we have: \n\n"""  # Edit this text as needed
    try:
        for output in app.stream({'question': 'How does the New Patriotic Party want to improve the ghanaian economy?'},
                                 config=config):
            for key, value in output.items():
                logging.info(f'Node: {key}\n---\n')
        print(value['generation'])
    except Exception as e:
        # logging.error("Graph recursion limit reached.")
        # Output the last generation with the preamble
        print(preamble)
        # if 'value' in locals():
        #     print(preamble + value['generation'])
        # else:
        #     print(preamble + value['generation'])
