# eval_prompts.py

from langchain_core.prompts import PromptTemplate

EVALUATION_PROMPT_TEXT = """
You are tasked with classifying the level of agreement between a political party's response and a user's response to a given question.

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
  1. `"agreement_classification"`: One of the five categories above.
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

WORKABLE_ANSWER_TEST_PROMPT = """
Given is a political question ({question}) and the user was tasked to input his custom answer: {user_response}.
We now want to proceed to compare this answer with the answers the party gave to that same political question.
However we first need to know if it is even possible to draw parralels between the response provided by the user and the response given by the party.

If the texts can be compared, answer with a "1", else with a "0".
"""
 
GENERATE_LOOKUP_PROMPT_TEXT = """
Given is a political question ({question}) and the user was tasked to input his custom answer: {user_response}.
Based on the information content in this response generate UP TO 5 PROMPTS (but can be less if the information content is small)
we can send to our embedding model to retrieve related information in the party programmes stored in our database.
Output the prompts in the JSON format like this:

{"lookupPrompts": ["prompt1", ... "prompt5"]}

ONLY output the JSON and no other text whatsoever.
"""

EVALUATION_PROMPT2_TEXT = """
You are tasked with classifying the level of agreement between a political party's response and a user's response to a given question.
For this we provided you ALL the political parties' responses to the specific question:

### Inputs:
- **Main Parties**: {main_parties}
- **Question**: "{question}"
- **Party Responses**: {party_responses}
- **User Response**: {user_response}

- **Main Contexts**: {main_contexts}

### Task:
Quantify the user's response compared to the party's response into a number from 1 to 100. The numbers should mirror the following sentiments when making the comparison:
- 0-20: The content of the user's response and the content of the party's response strongly disagree
- 20-40: The content of the user's response and the content of the party's response disagree
- 40-60: The content of the user's response and the content of the party's response neither coherently agree nor disagree
- 60-80: The content of the user's response and the content of the party's response agree
- 80-100: The content of the user's response and the content of the party's response strongly agree

In order to infer the agreement always take the contexts for the respective parties into consideration!

### Output Format:
- Respond **strictly in JSON format** with no additional text, headers, or labels (e.g., do not include "json" or other non-JSON content).
- Your JSON response must include two keys for EVERY PARTY:
  1. `"reasoning"`: A concise explanation for your classification.
  2. `"agreement_score"`: A value between 0 and 100
    

### Task Execution:
Now, evaluate the following:
- **Main Parties**: {main_parties}
- **Question**: "{question}"
- **Party Responses**: {party_responses}
- **User Response**: {user_response}

taking into account the contexts:
- **Main Contexts**: {main_contexts}

Respond strictly in JSON format without any extra text or labels.
"""

GENERATE_STANCE_PROMPT_TEXT = """Analyze the following political party documents and generate a concise summary 
of the party's stance on this specific question. Follow these guidelines:
1. Focus on key policy positions and priorities
2. Highlight any notable recent decisions or statements
3. Mention both supporting arguments and criticisms if present
4. Keep it under 150 words
5. Use formal but accessible language

Question: {question}

Relevant Document Excerpts:
{contexts}

Party: {party}
Summary:
"""

EVALUATION_PROMPT = PromptTemplate.from_template(EVALUATION_PROMPT_TEXT)
GENERATE_LOOKUP_PROMPT = PromptTemplate.from_template(GENERATE_LOOKUP_PROMPT_TEXT)
EVALUATION_PROMPT2 = PromptTemplate.from_template(EVALUATION_PROMPT2_TEXT)
GENERATE_STANCE_PROMPT = PromptTemplate.from_template(GENERATE_STANCE_PROMPT_TEXT)