import logging

def DEFAULT_RESPONSE(country: str):
    logging.debug(f"No question parameter found, resorting to default response.")
    return {"response": f"Hi, I am the chat assistant for {country}. Please ask me any question you have!"}