from ..models import SupportedLanguages

query_generation_instructions = {
    SupportedLanguages.EN: "Write a search query that will find helpful information for answering the user's question accurately. If you need more than one search query, write a list of search queries. If you decide that a search is very unlikely to find information that would be useful in constructing a response to the user, you should instead directly answer.",
    SupportedLanguages.DE: "Schreibe eine Suchanfrage, die hilfreiche Informationen liefert, um die Frage des Nutzers genau zu beantworten. Falls du mehr als eine Suchanfrage benötigst, erstelle eine Liste von Suchanfragen. Falls du entscheidest, dass eine Suche sehr wahrscheinlich keine nützlichen Informationen für die Beantwortung der Frage liefern wird, dann beantworte die Frage stattdessen direkt.",
}
