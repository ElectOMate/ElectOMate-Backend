from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class SupportedCountries(str, Enum):
    # GH = "GH"
    DE = "DE"
    
class Question(BaseModel):
    q: Optional[str] = Field(
        max_length=500,
        description="The question asked to the RAG pipeline."
    )
    
class Response(BaseModel):
    r: str = Field(
        description="The response of the RAG pipeline."
    )