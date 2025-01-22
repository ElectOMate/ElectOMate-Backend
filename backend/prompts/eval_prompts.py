from langchain_core.prompts import PromptTemplate

EVALUATION_PROMPT_TEXT = """
You are tasked with classifying the similarity between a political party's response and a user's response to a given question.

### Inputs:
- **Party**: {party}
- **Question**: "{question}"
- **Party Response**: {party_response}
- **User Response**: {user_response}

### Task:
Classify the user's response compared to the party's response into one of the following categories:
- strongly disagree
- disagree
- neutral
- agree
- strongly agree

### Output Format:
- Respond **strictly in JSON format** with no additional text, headers, or labels (e.g., do not include "json" or other non-JSON content).
- Your JSON response must include two keys:
  1. `"similarity_classification"`: One of the five categories above.
  2. `"reasoning"`: A concise explanation for your classification.

### Examples:
Example 1:
{{
    "agreement_classification": "agree",
    "reasoning": "The party and user seem to share a similar opinion that increased military support to Ukraine is not in the best interest of the German people."
}}
Example 2:
{{
    "agreement_classification": "strongly disagree",
    "reasoning": "The CDU/CSU party is generally critical of increasing the CO2 tax in Germany, while the user seems to believe it is a necessary step in ensuring Germany plays its part in reducing climate change."
}}

### Task Execution:
Now, evaluate the following:
- Party: {party}
- Question: "{question}"
- Party Response: {party_response}
- User Response: {user_response}

Respond strictly in JSON format without any extra text or labels.
"""

EVALUATION_PROMPT = PromptTemplate.from_template(EVALUATION_PROMPT_TEXT)