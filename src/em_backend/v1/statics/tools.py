from em_backend.v1.langchain_citation_client import ToolV2, ToolV2Function
from em_backend.old_models import SupportedLanguages

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
                    "enum": ["DE"],  # Nur deutsche Anfragen zulassen
                },
                "question_body": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Die politische Frage, die nachgeschlagen werden soll",
                        }
                    },
                    "required": ["question"],
                },
            },
            "required": ["country_code", "question_body"],
        },
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
                    "enum": ["EN"],  # Only allow German queries for now
                },
                "question_body": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The political question to look up",
                        }
                    },
                    "required": ["question"],
                },
            },
            "required": ["country_code", "question_body"],
        },
    },
}

database_search_tools = {
    SupportedLanguages.EN: ToolV2(
        type="function",
        function=ToolV2Function(
            name="database_search",
            description="Performs a database search through party manifestos of AFD, BSW, CDU, FDP, GRUNE, LINKE, SPD",
            parameters={
                "type": "object",
                "properties": {
                    "search_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "a list of queries for a text and vector similarity search in a database",
                    }
                },
                "required": ["search_queries"],
            },
        ),
    ),
    SupportedLanguages.DE: ToolV2(
        type="function",
        function=ToolV2Function(
            name="database_search",
            description="Führt eine Datenbanksuche in den Parteiprogrammen von AfD, BSW, CDU, FDP, GRÜNE, LINKE, SPD durch",
            parameters={
                "type": "object",
                "properties": {
                    "search_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Eine Liste von Suchanfragen für eine Text- und Vektorsimilaritätssuche in einer Datenbank",
                    }
                },
                "required": ["search_queries"],
            },
        ),
    ),
}

web_search_tools = {
    SupportedLanguages.EN: ToolV2(
        type="function",
        function=ToolV2Function(
            name="web_search",
            description="Performs a web search through web pages and news articles with the specified query",
            parameters={
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "The search query to pass to the search engine",
                    }
                },
                "required": ["search_query"],
            },
        ),
    ),
    SupportedLanguages.DE: ToolV2(
        type="function",
        function=ToolV2Function(
            name="web_search",
            description="Führt eine Websuche durch Webseiten und Nachrichtenartikel mit der angegebenen Suchanfrage durch",
            parameters={
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "Die Suchanfrage, die an die Suchmaschine übergeben wird",
                    }
                },
                "required": ["search_query"],
            },
        ),
    ),
}
