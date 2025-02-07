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
    SupportedLanguages.DE: {
        "type": "function",
        "name": "fetchRagData",
        "description": "Ruft verifizierte politische Informationen aus unserem RAG-System ab.",
        "parameters": {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "Der Ländercode (z.B. 'de' für Deutschland)",
                    "enum": ["DE"]  # Nur deutsche Anfragen zulassen
                },
                "question_body": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Die politische Frage, die nachgeschlagen werden soll"
                        }
                    },
                    "required": ["question"]
                }
            },
            "required": ["country_code", "question_body"]
        }
    },
    SupportedLanguages.EN: {
                        "type": "function",
                        "name": "fetchRagData",
                        "description": "Retrieves verified political information from our RAG system",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "country_code": {
                                    "type": "string",
                                    "description": "The country code (e.g., 'de' for Germany)",
                                    "enum": ["EN"]  # Only allow German queries for now
                                },
                                "question_body": {
                                    "type": "object",
                                    "properties": {
                                        "question": {
                                            "type": "string",
                                            "description": "The political question to look up"
                                        }
                                    },
                                    "required": ["question"]
                                }
                            },
                            "required": ["country_code", "question_body"]
                        }
                    }
                
}

