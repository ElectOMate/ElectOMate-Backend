# bing_litellm.py

import os
import markdown
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import uuid

router = APIRouter()

from dotenv import load_dotenv

load_dotenv()  # This will load the .env file into the environment

# Retrieve environment variables
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY")
BING_API_KEY = os.environ.get("BING_API_KEY")
LITELLM_API_BASE_URL = "https://litellm.sph-prod.ethz.ch/chat/completions"

if not LITELLM_API_KEY:
    raise ValueError("LITELLM_API_KEY is missing. Please set it in your .env file.")
if not BING_API_KEY:
    raise ValueError("BING_API_KEY must be set in your .env file.")

class SearchQuery(BaseModel):
    question: str


class FollowUpPayload(BaseModel):
    question: str
    sessionId: str










# @router.post("/search")
# async def search_route(query: SearchQuery) -> dict:
#     try:
#         if not query.question:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Query parameter 'question' is required"
#             )

#         # ---------------------------------------------------
#         # 1) MOCK BING DATA: Instead of calling Bing’s API,
#         #    we just return a hard-coded list of results.
#         # ---------------------------------------------------
#         results = [
#             {
#                 "title": "Example Title 1 Example Title 1 Example Title 1",
#                 "url": "http://example.com/1example.com/1example.com/1example.com/1example.com/1",
#                 "snippet": "This is a snippet snippet snippet snippet from example 1."
#             },
#             {"title": "EEExample Title 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
#             {"title": "Example Title 3", "url": "http://example.com/3", "snippet": "Snippet 3"},
#             {"title": "Example Title 4", "url": "http://example.com/4", "snippet": "Snippet 4"},
#             {"title": "Example Title 5", "url": "http://example.com/5", "snippet": "Snippet 5"},
#             {"title": "Example Title 6", "url": "http://example.com/6", "snippet": "Snippet 6"},
#             {"title": "Example Title 7", "url": "http://example.com/7", "snippet": "Snippet 7"},
#             {"title": "Example Title 8", "url": "http://example.com/8", "snippet": "Snippet 8"},
#             {"title": "Example Title 9", "url": "http://example.com/9", "snippet": "Snippet 9"},
#             {"title": "Example Title 10", "url": "http://example.com/10", "snippet": "Snippet 10"},
#         ]

#         # Simulate a stored “chat session”
#         session_id = "mock_session_id"
#         messages = [
#             {"role": "user", "content": query.question}
#         ]
#         chat_sessions = {session_id: messages}

#         # ---------------------------------------------------
#         # 2) SYSTEM PROMPT (Just building a string from
#         #    the mock Bing results).
#         # ---------------------------------------------------
#         # Note: chr(10) is a literal newline (\n).
#         system_prompt = (
#             "You are a helpful AI assistant. The user asked a question. "
#             "You have these Bing results:\n\n"
#             + "\n\n".join(
#                 [
#                     f"({i+1}) \"{r['title']}\"\nURL: {r['url']}\nSnippet: {r['snippet']}"
#                     for i, r in enumerate(results)
#                 ]
#             )
#             + "\n\nAnswer concisely, referencing the results if needed."
#         )

#         session_messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": query.question},
#         ]

#         # ---------------------------------------------------
#         # 3) MOCK LITE-LLM OUTPUT:
#         #    Instead of calling the real LiteLLM, we return
#         #    a fixed chunk of text.
#         # ---------------------------------------------------
#         text = """
# To compare the key differences between CDU and SPD, we can look at their recent political platforms. Here are some summarized points:

# **CDU (Christian Democratic Union):**
# - Focus on economic growth and competitiveness.
# - Lower taxes and reduce burdens on low-income earners.

# **SPD (Social Democratic Party of Germany):**
# - Focus on social justice and reducing income inequality.
# - Advocate for fair wages and stronger workers' rights.

# For detailed comparisons, you can refer to sources like the tagesschau.de comparison of party programs.
#         """.strip()

#         # Convert to Markdown for front-end usage
#         formatted_text = await formatResponseToMarkdown(text)

#         # Print the final “assistant” text to your console
#         print("LiteLLM Response:", formatted_text)

#         # Update our “chat sessions”
#         updated = messages + [{"role": "assistant", "content": text}]
#         chat_sessions[session_id] = updated

#         # Return data in JSON form
#         return {
#             "sessionId": session_id,
#             "summary": formatted_text,
#             "sources": results,
#         }

#     except Exception as error:
#         print("Search error:", error)
#         return {
#             "status": 500,
#             "message": str(error) or "An error occurred while processing your search",
#         }

# async def formatResponseToMarkdown(text: str) -> str:
#     """
#     A helper to convert plain text (or pseudo-Markdown) into HTML for front-end consumption.
#     """
#     processed_text = text.replace("\r\n", "\n")
#     return markdown.markdown(processed_text, extensions=['extra', 'nl2br'])






# In-memory storage for chat sessions
chat_sessions = {}

def generate_session_id() -> str:
    """Generate a simple unique session ID."""
    return uuid.uuid4().hex[:10]


def search_bing(query: str, count: int = 5) -> list[dict]:
    """
    Perform a Bing web search.
    Returns a list of dicts, each containing 'title', 'url', and 'snippet'.
    """
    BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
    params = {
        "q": query,
        "count": count,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": BING_API_KEY
    }

    response = requests.get(BING_ENDPOINT, params=params, headers=headers)
    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=f"Bing Search failed: {response.status_code} {response.reason}",
        )

    data = response.json()
    webPages = data.get("webPages", {}).get("value", [])

    # Log the query and the URLs of the search results
    print(f"Bing Search Query: {query}")
    for idx, page in enumerate(webPages):
        print(f"Result {idx+1} URL: {page['url']}")

    results = []
    for page in webPages[:count]:
        results.append({
            "title": page.get("name", ""),
            "url": page.get("url", ""),
            "snippet": page.get("snippet", "")
        })
    return results


def format_response_to_markdown(text: str) -> str:
    """
    Convert raw text to Markdown (HTML) with line breaks.
    Uses python-markdown with 'extra' and 'nl2br' extensions.
    """
    processed_text = text.replace("\r\n", "\n")
    return markdown.markdown(processed_text, extensions=["extra", "nl2br"])


def call_litellm(
    messages: list[dict],
    model: str = "gpt-4o",
    temperature: float = 0.8
) -> str:
    """
    Call the LiteLLM API with the provided messages and model.
    Each message is a dict: {'role': 'user'|'system'|'assistant', 'content': '...'}
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LITELLM_API_KEY}",
    }

    response = requests.post(LITELLM_API_BASE_URL, json=payload, headers=headers)
    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=f"LiteLLM API error: {response.status_code} {response.reason}",
        )

    data = response.json()
    # Return the text from the first choice, or a fallback message
    return data.get("choices", [{}])[0].get("message", {}).get("content", "No response from LiteLLM.")











@router.post("/search")
async def search_route(query: SearchQuery) -> dict:
    try:
        if not query.question:
            raise HTTPException(
                status_code=400,
                detail="Query parameter 'question' is required"
            )

        
        # Modify the query or keep as is
        modified_query = f"tagesschau {query.question}"
        results = search_bing(modified_query, count=5)

        session_id = generate_session_id()
        # Basic chat session: store user’s question
        messages = [{"role": "user", "content": query.question}]
        chat_sessions[session_id] = messages



        # Build a “system prompt” referencing the Bing results
        # (In practice, you might want more logic, additional context, etc.)
        system_prompt_lines = []
        system_prompt_lines.append("You are a helpful AI assistant. The user asked a question.")
        system_prompt_lines.append("You have these Bing results:\n")
        for i, r in enumerate(results):
            system_prompt_lines.append(f"({i+1}) \"{r['title']}\"\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
        system_prompt_lines.append("Answer concisely, referencing the results if needed.")
        system_prompt = "\n".join(system_prompt_lines)

        session_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query.question},
        ]

   

    # Call LLM
        try:
            raw_llm_response = call_litellm(session_messages, model="gpt-4o")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        

        
             # Convert LLM response to HTML via Markdown
        formatted_response = format_response_to_markdown(raw_llm_response)


        # Update chat history
        messages.append({"role": "assistant", "content": raw_llm_response})
        chat_sessions[session_id] = messages




        # Return data in JSON form
        return {
            "sessionId": session_id,
            "summary": formatted_response,
            "sources": results,
        }

    except Exception as error:
        print("Search error:", error)
        return {
            "status": 500,
            "message": str(error) or "An error occurred while processing your search",
        }

async def formatResponseToMarkdown(text: str) -> str:
    """
    A helper to convert plain text (or pseudo-Markdown) into HTML for front-end consumption.
    """
    processed_text = text.replace("\r\n", "\n")
    return markdown.markdown(processed_text, extensions=['extra', 'nl2br'])











@router.post("/follow-up")
async def search_route( payload: FollowUpPayload) -> dict:
    try:
        if not payload.question:
            raise HTTPException(
                status_code=400,
                detail="Query parameter 'question' is required"
            )


        if not payload.sessionId or not payload.question:
                raise HTTPException(status_code=400, detail="Both sessionId and query are required")

        session_messages = chat_sessions.get(payload.sessionId)
        if not session_messages:
                raise HTTPException(status_code=404, detail="Chat session not found")

        # Additional Bing search for the follow-up
        results = search_bing(payload.question, count=5)

        # Add the new user message
        user_message = {"role": "user", "content": payload.question}
        new_messages = session_messages + [user_message]

        # Build an updated system message referencing the new Bing results
        system_followup_lines = ["More Bing results for the user's follow-up:\n"]
        for i, r in enumerate(results):
            system_followup_lines.append(f"({i+1}) \"{r['title']}\"\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
        system_followup_lines.append("Please refine or expand your answer with these details.")
        system_followup = "\n".join(system_followup_lines)

        # Put everything together for the next LLM call
        messages_for_llm = [{"role": "system", "content": system_followup}] + new_messages

        
        
        try:
            raw_llm_response = call_litellm(messages_for_llm, model="claude-3-5-sonnet")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        formatted_response = format_response_to_markdown(raw_llm_response)

        # Now store the assistant’s new response
        new_messages.append({"role": "assistant", "content": raw_llm_response})
        chat_sessions[payload.sessionId] = new_messages




#         # ---------------------------------------------------
#         # 1) MOCK BING DATA: Instead of calling Bing’s API,
#         #    we just return a hard-coded list of results.
#         # ---------------------------------------------------
#         results = [
#             {
#                 "title": "Example Title 1 Example Title 1 Example Title 1",
#                 "url": "http://example.com/1example.com/1example.com/1example.com/1example.com/1",
#                 "snippet": "This is a snippet snippet snippet snippet from example 1."
#             },
#             {"title": "EEExample Title 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
#             {"title": "Example Title 3", "url": "http://example.com/3", "snippet": "Snippet 3"},
#             {"title": "Example Title 4", "url": "http://example.com/4", "snippet": "Snippet 4"},
#             {"title": "Example Title 5", "url": "http://example.com/5", "snippet": "Snippet 5"},
#             {"title": "Example Title 6", "url": "http://example.com/6", "snippet": "Snippet 6"},
#             {"title": "Example Title 7", "url": "http://example.com/7", "snippet": "Snippet 7"},
#             {"title": "Example Title 8", "url": "http://example.com/8", "snippet": "Snippet 8"},
#             {"title": "Example Title 9", "url": "http://example.com/9", "snippet": "Snippet 9"},
#             {"title": "Example Title 10", "url": "http://example.com/10", "snippet": "Snippet 10"},
#         ]

#         # Simulate a stored “chat session”
#         session_id = "mock_session_id"
#         messages = [
#             {"role": "user", "content": query.question}
#         ]
#         chat_sessions = {session_id: messages}

#         # ---------------------------------------------------
#         # 2) SYSTEM PROMPT (Just building a string from
#         #    the mock Bing results).
#         # ---------------------------------------------------
#         # Note: chr(10) is a literal newline (\n).
#         system_prompt = (
#             "You are a helpful AI assistant. The user asked a question. "
#             "You have these Bing results:\n\n"
#             + "\n\n".join(
#                 [
#                     f"({i+1}) \"{r['title']}\"\nURL: {r['url']}\nSnippet: {r['snippet']}"
#                     for i, r in enumerate(results)
#                 ]
#             )
#             + "\n\nAnswer concisely, referencing the results if needed."
#         )

#         session_messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": query.question},
#         ]

#         # ---------------------------------------------------
#         # 3) MOCK LITE-LLM OUTPUT:
#         #    Instead of calling the real LiteLLM, we return
#         #    a fixed chunk of text.
#         # ---------------------------------------------------
#         text = """
# To compare the key differences between CDU and SPD, we can look at their recent political platforms. Here are some summarized points:

# **CDU (Christian Democratic Union):**
# - Focus on economic growth and competitiveness.
# - Lower taxes and reduce burdens on low-income earners.

# **SPD (Social Democratic Party of Germany):**
# - Focus on social justice and reducing income inequality.
# - Advocate for fair wages and stronger workers' rights.

# For detailed comparisons, you can refer to sources like the tagesschau.de comparison of party programs.
#         """.strip()

#         # Convert to Markdown for front-end usage
#         formatted_text = await formatResponseToMarkdown(text)

#         # Print the final “assistant” text to your console
#         print("LiteLLM Response:", formatted_text)

#         # Update our “chat sessions”
#         updated = messages + [{"role": "assistant", "content": text}]
#         chat_sessions[session_id] = updated

        # Return data in JSON form
        return {
            "summary": formatted_response,
            "sources": results,
        }

    except Exception as error:
        print("Search error:", error)
        return {
            "status": 500,
            "message": str(error) or "An error occurred while processing your search",
        }
