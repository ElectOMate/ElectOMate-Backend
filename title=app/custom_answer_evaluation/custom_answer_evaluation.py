import json

@@ async def compare_user_response_to_party(
        print(prompt_content) # Debug: print the prompt content
        # Force the conversion: extract the plain string from prompt_content
        plain_prompt = prompt_content.text
        print(plain_prompt)  # Debug: print the plain text prompt
        messages = [UserChatMessageV2(content=plain_prompt)]
        print(messages)      # Debug: print the chat message object
        evaluation_response = await cohere_async_clients["command_r_async_client"].chat(
            model="command-r-08-2024",
            messages=messages
        )
        # Extract the chat response text from the first generation:
        evaluation_text = evaluation_response.generations[0].text
        evaluation_dict = json.loads(evaluation_text)   