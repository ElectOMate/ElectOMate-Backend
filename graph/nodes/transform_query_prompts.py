system_prompt = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval. 
Look at the input and try to reason about the underlying semantic intent / meaning. Only output the new question. 
It should contain as good keywords as possible for the retrieval augmented generation as possible.
"""

human_prompt_1 = "Question: Tell me more about the New Patriotic Party?:"
assistant_prompt_1 = "explain the standpoints of new patriotic party in ghana generally"
human_prompt_2 = "Here is the initial question: \n\n {question} \n\nFormulate an improved question."
