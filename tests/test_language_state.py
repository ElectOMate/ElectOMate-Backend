from em_backend.agent.language import (
    LanguageContextPayload,
    LanguageDescriptor,
    initialize_language_state,
)
from langchain_core.messages import AIMessage, HumanMessage


def _make_messages(*contents: str) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    for idx, content in enumerate(contents, start=1):
        if idx % 2:
            messages.append(HumanMessage(id=f"human-{idx}", content=content))
        else:
            messages.append(AIMessage(id=f"ai-{idx}", content=content))
    return messages


def test_initialize_language_state_prompts_confirmation_for_language_switch() -> None:
    messages = _make_messages("Hallo, kannst du mir helfen?")
    context = LanguageContextPayload(
        selected_language=LanguageDescriptor(name="English", code="en", flag="gb"),
        manifesto_language=LanguageDescriptor(name="Deutsch", code="de", flag="de"),
        available_languages=[
            LanguageDescriptor(name="English", code="en", flag="gb"),
            LanguageDescriptor(name="Deutsch", code="de", flag="de"),
        ],
        respond_in_user_language=True,
    )

    language_state = initialize_language_state(messages, context)

    assert language_state["preferred_language"]["code"] == "en"
    assert language_state["conversation_language"]["code"] == "en"
    assert language_state["latest_user_language"]["code"] == "de"
    assert language_state["pending_language_confirmation"] is True


def test_initialize_language_state_respects_existing_conversation_language() -> None:
    messages = _make_messages("Bonjour, comment ça va ?")
    context = LanguageContextPayload(
        selected_language=LanguageDescriptor(name="English", code="en", flag="gb"),
        manifesto_language=LanguageDescriptor(name="Français", code="fr", flag="fr"),
        conversation_language=LanguageDescriptor(
            name="Français", code="fr", flag="fr"
        ),
        available_languages=[
            LanguageDescriptor(name="English", code="en", flag="gb"),
            LanguageDescriptor(name="Français", code="fr", flag="fr"),
        ],
        respond_in_user_language=True,
        language_preference={
            "language": {"name": "Français", "code": "fr", "flag": "fr"},
            "decision": "accepted",
        },
    )

    language_state = initialize_language_state(messages, context)

    assert language_state["conversation_language"]["code"] == "fr"
    assert language_state["pending_language_confirmation"] is False


def test_initialize_language_state_detects_spanish_without_greeting_keyword() -> None:
    messages = _make_messages("¿Puedes explicarme las propuestas del partido?")
    context = LanguageContextPayload(
        selected_language=LanguageDescriptor(name="English", code="en", flag="gb"),
        manifesto_language=LanguageDescriptor(name="Español", code="es", flag="es"),
        available_languages=[
            LanguageDescriptor(name="English", code="en", flag="gb"),
            LanguageDescriptor(name="Español", code="es", flag="es"),
        ],
        respond_in_user_language=True,
    )

    language_state = initialize_language_state(messages, context)

    assert language_state["latest_user_language"] is not None
    assert language_state["latest_user_language"]["code"] == "es"
