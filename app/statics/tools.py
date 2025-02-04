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

realtime_session_tools = {
    SupportedLanguages.EN: {
        "type": "function",
        "name": "fetchRagData",
        "description": "Retrieves verified political information from ourdatabase.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "The country code corresponding to the language of the conversation",
                    "enum": ["DE", "EN"],
                },
                "question": {
                    "type": "string",
                    "description": "A question related to the 2025 German Federal Elections that will be answered in a fact-based manner",
                },
            },
            "required": ["country_code", "question"],
            "additionalProperties": False,
        },
    },
    SupportedLanguages.DE: {
        "type": "function",
        "name": "fetchRagData",
        "description": "Ruft verifizierte politische Informationen aus unserer Datenbank ab.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "Der Ländercode, der der Sprache des Gesprächs entspricht.",
                    "enum": ["DE", "EN"],
                },
                "question": {
                    "type": "string",
                    "description": "Eine Frage zu den Bundestagswahlen 2025, die faktenbasiert beantwortet wird.",
                },
            },
            "required": ["country_code", "question"],
            "additionalProperties": False,
        },
    },
}
