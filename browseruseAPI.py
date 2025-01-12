# browseruseAPI.py

import uvicorn
import asyncio
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState  # For state checks

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller
from browser_use.agent.service import Agent
from langchain_openai import ChatOpenAI
from playwright.async_api import Page

app = FastAPI()

# Global references for demonstration only
global_browser = None
global_context = None
global_agent = None

@app.on_event("startup")
async def on_startup():
    """
    Spin up the browser in the background to be used by any client connection
    """
    global global_browser, global_context

    global_browser = Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=True
        )
    )
    global_context = await global_browser.new_context()
    page = await global_context.get_current_page()
    await page.goto("about:blank")


@app.on_event("shutdown")
async def on_shutdown():
    """
    Cleanly close resources
    """
    global global_browser
    if global_browser:
        await global_browser.close()
        global_browser = None


@app.get("/")
def root():
    """
    Return a simple HTML to instruct user to open /frontend
    """
    return HTMLResponse("<h1>Go to the front-end page to see streaming!</h1>")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to:
      1) Accept instructions from user
      2) Execute in the browser
      3) Return ongoing screenshot frames
    """
    await websocket.accept()

    global global_agent, global_context
    if not global_agent:
        controller = Controller()
        model = ChatOpenAI(model="gpt-4o")
        global_agent = Agent(
            task="(Empty task, we'll control it with manual instructions)",
            llm=model,
            controller=controller,
            browser_context=global_context
        )

    sending_frames = True

    async def send_frames_loop():
        while sending_frames:
            try:
                page = await global_context.get_current_page()
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                await websocket.send_json({"type": "frame", "data": screenshot_b64})
                await asyncio.sleep(1.0)
            except Exception as ex:
                print("Error sending frames:", ex)
                break

    frame_task = asyncio.create_task(send_frames_loop())

    try:
        while True:
            msg = await websocket.receive_text()

            if msg.startswith("goto "):
                url = msg.replace("goto ", "").strip()
                page = await global_context.get_current_page()
                await page.goto(url)
            elif msg.startswith("scroll"):
                page = await global_context.get_current_page()
                await page.evaluate("window.scrollBy(0, 400);")
            elif msg.startswith("done"):
                await websocket.send_text("Okay, finishing up!")
                break
            else:
                await websocket.send_text(f"Received unknown instruction: {msg}")

            await websocket.send_text(f"Executed command: {msg}")

    except WebSocketDisconnect as e:
        print("Client disconnected.")
        print(f"WebSocket error: {e}")
    finally:
        # Stop sending frames
        sending_frames = False
        frame_task.cancel()
        try:
            await frame_task
        except asyncio.CancelledError:
            pass

        # If still connected, close the socket
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()


if __name__ == "__main__":
    uvicorn.run("browseruseAPI:app", host="0.0.0.0", port=8000, reload=True)