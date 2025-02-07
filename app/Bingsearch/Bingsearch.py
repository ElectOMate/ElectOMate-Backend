import os
import uuid
import requests
import markdown
import httpx

from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel
import cohere
import httpx
from app.config import settings , bing_client  # Import the settings

# -----------------------
# Load environment
# -----------------------
load_dotenv('../.env')  # Adjust path if needed

COHERE_API_KEY = os.getenv('COMMAND_R_API_KEY')
COHERE_BASE_URL = os.getenv('COMMAND_R_URL')
BING_API_KEY = os.getenv("BING_API_KEY")

if not COHERE_API_KEY or not COHERE_BASE_URL:
    raise ValueError("Missing Cohere API credentials in environment variables.")
if not BING_API_KEY:
    raise ValueError("Missing Bing API Key in environment variables.")

# -----------------------
# COHERE CLIENT SETUP
# -----------------------

cohere_async_clients = {
    "command_r_async_client": cohere.AsyncClientV2(
        api_key=settings.command_r_api_key, base_url=settings.command_r_url
    ),
    # ... other clients if needed ...
}

# -----------------------
# Helper / model classes
# -----------------------
class SearchQuery(BaseModel):
    question: str

# For demonstration only; if you don't need session logic, you can remove it.
chat_sessions = {}

def generate_session_id() -> str:
    """Generate a simple unique session ID."""
    return uuid.uuid4().hex[:10]

# -----------------------
# Bing Search
# -----------------------
def search_bing(query: str, count: int = 5) -> list[dict]:
    """
    Perform a Bing web search via Azure. 
    Returns a list of dicts, each containing 'title', 'url', and 'snippet'.
    """
    response = bing_client.search(query, count)  # Use the Bing client
    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=f"Bing Search failed: {response.status_code} {response.reason}",
        )

    data = response.json()
    web_pages = data.get("webPages", {}).get("value", [])

    # Optional debug logging
    print(f"Bing Search Query: {query}")
    for idx, page in enumerate(web_pages):
        print(f"Result {idx+1} URL: {page['url']}")

    results = []
    for page in web_pages[:count]:
        results.append({
            "title": page.get("name", ""),
            "url": page.get("url", ""),
            "snippet": page.get("snippet", "")
        })
    return results

# -----------------------
# Markdown formatting
# -----------------------
def format_response_to_markdown(text: str) -> str:
    """
    Convert raw text to Markdown (HTML) with line breaks.
    Uses python-markdown with 'extra' and 'nl2br' extensions.
    """
    processed_text = text.replace("\r\n", "\n")
    return markdown.markdown(processed_text, extensions=["extra", "nl2br"])

# -----------------------
# Cohere Chat Call
# -----------------------
async def call_cohere_chat(
    messages: list[dict], 
    model: str = "command-r-08-2024", 
    temperature: float = 0.8
) -> str:
    """
    Calls Cohere's async chat endpoint to get a single (non-streamed) response.
    `messages` is a list of dicts: [{"role": "system"|"user"|"assistant", "content": "..."}].
    """
    try:
        # Non-streaming chat response
        response = await cohere_async_clients["command_r_async_client"].chat(
            model=model,
            messages=messages,
            temperature=temperature
        )
        # The text response typically lives here:
        return response.message.content[0].text
    except httpx.ReadError:
        raise HTTPException(status_code=500, detail="Error reading response from Cohere.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# The main function: perform_search
# -----------------------
async def perform_search(query: dict) -> dict:
    """
    1. Retrieve the user question from `query`
    2. Perform a Bing search 
    3. Build a system prompt with the search results
    4. Call the Cohere model (async) to summarize
    5. Return final text plus the sources
    """
    try:
        user_question = query.get("question")
        if not user_question:
            raise HTTPException(
                status_code=400,
                detail="Query parameter 'question' is required"
            )

        # Example: add "tagesschau" or whatever to user query. If not desired, omit.
        modified_query = f"tagesschau {user_question}"
        results = search_bing(modified_query, count=5)

        # (Optional) session logic
        session_id = generate_session_id()
        chat_sessions[session_id] = [{"role": "user", "content": user_question}]

        # Build a system prompt referencing Bing results
        system_prompt_lines = ["""
You are a helpful AI assistant. The user asked a question. use the provided Bing results to answer the question. Format in Markdown. Use numbered bulletpoints and linebreaks and indents, headings and paragraphs with empty lines in between

Please generate your markdown output such that every URL reference is embedded using the following format:

  (see source [<reference_number>](<url>))

For example, if you reference a Tagesschau article, the link should appear exactly like:

  (see source [2](https://www.tagesschau.de/inland/innenpolitik/krankenhausreform-bundesrat-100.html))

Make sure that:
- The link text always contains a reference number inside square brackets (e.g., “[2]”).
- The overall format remains consistent across all links.

This exact format is required because our frontend will scan for the number within the link text and render a clickable green dot containing that number next to the link.
USE NUMBERED INDENTED BULLETPOINTS AND LINEBREAKS AND INDENTS, HEADINGS AND PARAGRAPHS WITH EMPTY LINES IN BETWEEN. ALWAYS RETURN SOURCES WITH LINKED URLS.

 """]

        system_prompt_lines.append("You have these Bing results:\n")
        for i, r in enumerate(results):
            system_prompt_lines.append(f"({i+1}) \"{r['title']}\"\nURL: {r['url']}\nSnippet: {r['snippet']}\n")

        system_prompt_lines.append("Answer concisely, referencing the results if needed.")
        system_prompt = "\n".join(system_prompt_lines)

        # Final messages list for Cohere chat
        messages_for_cohere = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ]

        # Call Cohere's Chat (non-streaming)
        raw_llm_response = await call_cohere_chat(messages_for_cohere, model="command-r-08-2024")

        # Optionally convert the text to HTML with Markdown
        formatted_response = format_response_to_markdown(raw_llm_response)

        # (Optional) store the assistant's answer in session
        chat_sessions[session_id].append({"role": "assistant", "content": raw_llm_response})

        # Return JSON with summary + sources
        return {
            "sessionId": session_id,
            "summary": raw_llm_response,   # or `formatted_response`
            "sources": results
        }

    except Exception as error:
        print("Search error:", error)
        return {
            "status": 500,
            "message": str(error) or "An error occurred while processing your search",
        }