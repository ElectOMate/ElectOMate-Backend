import sys
import os

# Add the current directory to the system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio

async def main():
    agent = Agent(
        task="Find a petition for taxing the rich causes in germany and sign it with a mock but valid email adress, öause for a moment if you pressed the button, to let me fill out the human verification or catpcha",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()
    print(result)

asyncio.run(main())