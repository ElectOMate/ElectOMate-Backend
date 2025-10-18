from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

REPHRASE_QUESTION = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

You analyze a users message to a chat system in the context of the ongoing conversation and have two tasks:

'# Tasks

Task 1: Formulate the users question in a general way, as if it were addressed directly to a single conversation partner without mentioning any names.
Example: From “What is the position of the Greens and the SPD on climate protection?” → “What is your position on climate protection?”

Task 2: Decide whether it is an explicit comparison question or not.
If the user explicitly asks to weigh or compare multiple parties directly against each other, respond with True.
In all other cases, respond with False.

# Language Requirements

Always return the rephrased question in {target_language_name}. Preserve tone and formality when translating. If the user's latest message uses a different language, translate the rephrased question into {target_language_name} while keeping the original meaning.

# Examples for other languages

Input: "Kannst du mir sagen, was eure Pläne für die Energiewende sind?"
Output: "Was ist eure Position zur Energiewende?"

Input: "¿Qué propone tu partido sobre la vivienda?"
Output: "¿Cuál es su postura sobre la política de vivienda?"

# Important Notes on Classifying Comparison Questions

A question is considered a comparison question (True) only if the user explicitly asks to directly compare the positions of multiple parties, e.g. by asking about differences, similarities, or a direct juxtaposition.

A question is not a comparison question (False) if it merely refers to multiple parties, but each party could answer individually without the user explicitly expecting a comparison.

# Examples

“How do the Greens and the SPD differ on climate protection?” → True (explicit question about differences).

“What is your position on climate protection?” → False (information about both positions individually, no direct comparison requested).

“Which party is better on climate protection, the Greens or the SPD?” → True (direct juxtaposition/evaluation requested).

“What are the positions of the AfD and the Greens on wind turbines?” → False (no explicit comparison, only asking for individual positions).
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


class RephraseQuestionStructuredOutput(BaseModel):
    rephrased_question: str = Field(
        description="The question rephrased without any party information."
    )
    is_comparison_question: bool = Field(
        description="The question asks for a comparison between two or more parties."
    )
