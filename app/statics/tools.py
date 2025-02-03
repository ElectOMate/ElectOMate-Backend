from cohere import ToolV2, ToolV2Function
from ..models import SupportedLanguages

query_generation_tools = {
    SupportedLanguages.EN: ToolV2(
        function=ToolV2Function(
            name="database_search",
            parameters={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "a list of queries for a text and similarity search in a database.",
                    }
                },
                "required": ["queries"],
            },
        )
    ),
    SupportedLanguages.DE: ToolV2(
        function=ToolV2Function(
            name="database_search",
            parameters={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "eine Liste von Anfragen für eine Text- und Ähnlichkeitssuche in einer Datenbank.",
                    }
                },
                "required": ["queries"],
            },
        )
    ),
}
