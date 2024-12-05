import logging.config
import azure.functions as func
import logging
from graph import get_graph
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
import json
from questions import match
from dotenv import load_dotenv

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="hi", auth_level=func.AuthLevel.ANONYMOUS)
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
        
# @app.route(route="chat", auth_level=func.AuthLevel.ANONYMOUS)
# def chat(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP chat function processed a request.')
#     preamble = """Our algorithm has reach our self-imposed recursion limit of 10. 
#     This means that we are not confident enough that the data in the context is enough to answer your question. 
#     However, we will still provide the best answer we can given the data we have: \n\n"""
#     question = req.params.get('question')
#     if not question:
#         try:
#             req_body = req.get_json()
#         except ValueError:
#             pass
#         else:
#             question = req_body.get('question')
    
#     if question:
#         app = get_graph()
#         config = RunnableConfig(recursion_limit=10)
#         try:
#             for output in app.stream({'question': question}, config=config):
#                 for key, value in output.items():
#                     logging.info(f'Node: {key} --- Value: {value}')
#             logging.info("Response correctly retrieved.")
#             try:
#                 return func.HttpResponse(
#                     value['generation'],
#                     status_code=200
#                 )
#             except:
#                 return func.HttpResponse(
#                     "Hi! Please provide a question relevant to the 2024 Ghanaian general election. Thank you!",
#                     status_code=200
#                 )
#         except GraphRecursionError:
#             for output in app.stream({'question': question}, config=config):
#                 for key, value in output.items():
#                     logging.info(f'Node: {key} --- Value: {value}')
#             logging.info("Response correctly retrieved.")
#             preamble = """Our algorithm has reach our self-imposed recursion limit of 10. 
#             This means that we are not confident enough that the data in the context is enough to answer your question. 
#             However, we will still provide the best answer we can given the data we have: \n\n"""
#             try:
#                 return func.HttpResponse(
#                     preamble + value['generation'],
#                     status_code=200
#                 )
#             except:
#                 return func.HttpResponse(
#                     "Hi! Please provide a question relevant to the 2024 Ghanaian general election. Thank you!",
#                     status_code=200
#                 )
#     else:
#         return func.HttpResponse(
#             "Incorrect HTTP request. Please provide either an HTTP header with name 'question' or a json body containing a 'question' entry.",
#             status_code=400
#         )



@app.route(route="chat", auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP chat function processed a request.')
    preamble = """Warning: Answer based on very limited darta found in the context. This can happen due to self-imposed safety settings."""
    
    # Retrieve the question from query parameters or JSON body
    question = req.params.get('question')
    if not question:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            question = req_body.get('question')
    
    if question:
        app_graph = get_graph()
        config = RunnableConfig(recursion_limit=10)
        generation = ""  # Initialize generation variable

        try:
            # Stream the outputs from the graph
            loopfix = False  # Initialize loopfix
            for output in app_graph.stream({'question': question}, config=config):
                for key, value in output.items():
                    logging.info(f'Node: {key} --- Value: {value}')
                    if 'generation' in value:
                        generation = value['generation']  # Update generation
                    if 'loopfix' in value:
                        loopfix = value['loopfix']  # Update loopfix

            logging.info("Response correctly retrieved.")
            if generation and loopfix:
                return func.HttpResponse(
                    generation + "\n\n\n" + preamble,
                    status_code=200
                )
            elif generation:
                return func.HttpResponse(
                    generation + "test",
                    status_code=200
                )
            else:
                # If generation is empty, return a default message
                return func.HttpResponse(
                    "Hi! Please provide a question relevant to the 2024 Ghanaian general election. Thank you!",
                    status_code=200
                )
        except GraphRecursionError:
            logging.error("GraphRecursionError occurred.")
            logging.info("Attempting to retrieve partial generation.")

            if generation:
                # Return preamble with partial generation
                return func.HttpResponse(
                     generation + "\n\n\n" + preamble,
                    status_code=200
                )
            else:
                # If no generation was captured, return the preamble alone
                return func.HttpResponse(
                    "Unfortunately, some error has occured, but we are logging this and will debug asap.",
                    status_code=200
                )
    else:
        return func.HttpResponse(
            "Incorrect HTTP request. Please provide either an HTTP header with name 'question' or a JSON body containing a 'question' entry.",
            status_code=400
        )
    

        
@app.route(route="match-party", auth_level=func.AuthLevel.ANONYMOUS)
def matchparty(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Puthon HTTP match-party function processed a request.") 
    
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Requires JSON payload",
            status_code=400
        )
    
    try:
        answer = match(req_body)
        return func.HttpResponse(
            json.dumps(answer),
            status_code=200
        )
    except:
        return func.HttpResponse(
            "Error generating response",
            status_code=400
        )