import logging.config
import azure.functions as func
import logging
from graph import get_graph
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="hi")
def hi(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP hi function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
        
@app.route(route="chat")
async def chat(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP chat function processed a request.')
    
    question = req.params.get('question')
    if not question:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            question = req_body.get('question')
    
    if question:
        app = get_graph()
        config = RunnableConfig(recursion_limit=10)
        try:
            for output in app.stream({'question': question}, config=config):
                for key, value in output.items():
                    logging.info(f'Node: {key}\n---\n')
            logging.info("Response correctly retrieved.")
            return func.HttpResponse(
                value['generation'],
                status_code=200
            )
        except GraphRecursionError:
            logging.error("Graph recursion limit reached.")
            return func.HttpResponse(
                "Langchain Graph Recursion limit reached. Sadly, our documents do not allow us to answer your question.",
                status_code=400
            )
    else:
        return func.HttpResponse(
            "Incorrect HTTP request. Please provide either an HTTP header with name 'question' or a json body containing a 'question' entry.",
            status_code=400
        )