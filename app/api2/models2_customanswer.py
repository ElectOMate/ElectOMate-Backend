from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class SupportedLanguages(str, Enum):
    DE = "de"
    EN = "en"

class CustomAnswerModel(BaseModel):
    question: str = Field(
        ...,
        max_length=500,
        description="The question for which the custom answer is provided."
    )
    custom_answer: str = Field(
        ...,
        description="The user's custom answer to the question."
    )
    wheights: Optional[str] = Field(
        None, 
        description="The discrete weight associated with the answer."
    )
    skipped: bool = Field(
        default=False,
        description="Flag indicating if the question was skipped."
    )

    class Config:
        schema_extra = {
            "example": {
                "question": "What is your opinion on increasing the defense budget?",
                "custom_answer": "I believe that a balanced approach is needed to support the military while maintaining fiscal responsibility.",
                "wheights": "neutral",
                "skipped": False
            }
        } 