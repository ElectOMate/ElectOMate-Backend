import os
import json
import asyncio

from pydantic import BaseModel
from typing import List, Dict
from app.config import Settings, weaviate_async_client, cohere_async_clients
from .eval_prompts import GENERATE_STANCE_PROMPT  
from weaviate.collections.classes.filters import Filter





# 1) Initialize settings
settings = Settings()

class QuestionInput(BaseModel):
    id: int
    text: str

class PartyStanceGenerator:
    def __init__(self):
        # Make sure these parties match what you actually want
        self.parties = [
            "SPD", "GRUENE", "FDP", "CDU/CSU", 
            "LINKE", "AFD", "FREIE WÄHLER", 
            "Volt", "MLPD", "BÜNDNIS DEUTSCHLAND", "BSW"
        ]

    async def get_party_contexts(self, party: str, question: str, max_contexts: int = 7) -> List[str]:
        """
        Vectorize the question and use the vector in the Weaviate query
        """
        try:
            # Vectorize the question using Cohere
            embed_response = await cohere_async_clients["embed_multilingual_async_client"].embed(
                texts=[question],
                model="embed-multilingual-v3.0",
                input_type="search_query",
                embedding_types=["float"]
            )
            
            # Access the embeddings correctly
            question_vector = embed_response.embeddings.float[0]  # Adjust this line based on the actual response structure

            collection = weaviate_async_client.collections.get("Documents")
            
            # Use the vector in the hybrid query
            result = await collection.query.hybrid(
                query=question,
                vector=question_vector,
                limit=max_contexts,
                filters=Filter.by_property("title").like(f"*{party}*")
            )

            contexts = []
            for obj in result.objects:
                chunk = obj.properties.get("chunk_content", "")
                if chunk:
                    contexts.append(chunk)

            return contexts

        except Exception as e:
            print(f"Error retrieving contexts for {party}: {str(e)}")
            return []

    async def generate_party_stance(self, party: str, question: str, contexts: List[str]) -> str:
        """
        Updated to use cohere_async_clients from config
        """
        try:
            prompt_str = GENERATE_STANCE_PROMPT.format(
                question=question,
                contexts="\n\n".join(contexts),
                party=party
            )

            cohere_client = cohere_async_clients["command_r_async_client"]
            response = await cohere_client.chat(
                messages=[{"role": "user", "content": prompt_str}],
                model="command-r-plus",
                temperature=0.3,
                max_tokens=500
            )

            return response.message.content[0].text
            
        except Exception as e:
            print(f"Error generating stance for {party}: {str(e)}")
            return ""

    async def process_question(self, question: QuestionInput, file_path: str):
        """
        For each party in self.parties, get contexts and generate stance text.
        Write results to file incrementally.
        """
        results = {}
        for party in self.parties:
            contexts = await self.get_party_contexts(party, question.text)
            if not contexts:
                print(f"No contexts found for {party} on question {question.id}")
                continue

            stance = await self.generate_party_stance(party, question.text, contexts)
            results[party] = stance
            print(f"Processed {party} for question {question.id}")

        # Write to file incrementally
        with open(file_path, "r+", encoding="utf-8") as f:
            # Load existing data
            f.seek(0)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

            # Update data with new results
            data[str(question.id)] = results

            # Write updated data back to file
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()


async def main():
    """
    Ensure clients are connected before use
    """
    try:
        # Connect the Weaviate client
        await weaviate_async_client.connect()

        # Load questions from Partyanswers.json
        with open('app/custom_answer_evaluation/Partyanswers.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            questions = [QuestionInput(id=q['id'], text=q['q']) for q in data['questions']]

        generator = PartyStanceGenerator()
        
        file_path = "custom_answer_evaluation/questionnaire_party_answers_NEW.json"
        # Initialize the file with an empty JSON object
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

        for question in questions:
            print(f"\nProcessing question {question.id}: {question.text}")
            await generator.process_question(question, file_path)

        print(f"Generation complete. File saved as {file_path}")

    finally:
        # Always gracefully close the clients if possible
        await weaviate_async_client.close()
        # If you have any other clients that need closing, do it here

if __name__ == "__main__":
    asyncio.run(main())