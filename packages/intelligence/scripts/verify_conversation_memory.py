"""Live verification: multi-turn conversation memory through Reason."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "packages" / "intelligence" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memovi_intelligence.application.commands import Reason
from memovi_intelligence.application.services import (
    ContextAssembler,
    ConversationService,
    ModelGateway,
    PromptBuilder,
)
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import RetrievedKnowledge
from memovi_intelligence.infrastructure import (
    FakeReasoningProvider,
    InMemoryConversationRepository,
)


class StubRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...]) -> None:
        self._items = items

    def retrieve(self, request: ReasoningRequest, *, limit: int) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def main() -> None:
    knowledge = (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-builder",
            document_id="doc-origin",
            text="Memovi is built by its project maintainers as an open platform.",
            score=0.90,
            document_title="Origin",
        ),
    )
    config = IntelligenceConfig(provider="fake")
    conversations = ConversationService(repository=InMemoryConversationRepository())
    retriever = StubRetriever(knowledge)
    assembler = ContextAssembler(knowledge_retriever=retriever, config=config)
    builder = PromptBuilder()
    reason = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        model_gateway=ModelGateway(
            providers={"fake": FakeReasoningProvider()},
            config=config,
        ),
        prompt_builder=builder,
    )

    conversation = conversations.create_conversation()
    print(f"conversation_id = {conversation.id.value}")

    # --- Turn 1 ---
    q1 = "What is Memovi?"
    result1 = reason.execute(ReasoningRequest.create(query=q1))
    conversations.append_user_turn(conversation.id, q1)
    conversations.append_assistant_turn(
        conversation.id,
        result1.answer,
        citations=result1.citations,
    )
    print("\n=== Turn 1 ===")
    print(f"user = {q1}")
    print(f"assistant_preview = {result1.answer[:180].replace(chr(10), ' ')}")

    # --- Turn 2 ---
    q2 = "Who built it?"
    history2 = conversations.load_history(conversation.id)
    result2 = reason.execute(
        ReasoningRequest.create(query=q2),
        conversation_history=history2,
    )
    conversations.append_user_turn(conversation.id, q2)
    conversations.append_assistant_turn(
        conversation.id,
        result2.answer,
        citations=result2.citations,
    )
    prompt2 = builder.build(result2.context)
    section_names = [section.name for section in prompt2.sections]
    history_text = prompt2.section("conversation_history").content
    knowledge_text = prompt2.section("retrieved_knowledge").content

    print("\n=== Turn 2 ===")
    print(f"user = {q2}")
    print(f"history_loaded = {len(history2.turns) == 2}")
    print(f"context_history_turn_count = {len(result2.context.conversation_history.turns)}")
    print(
        "context_history_roles = "
        f"{[turn.role.value for turn in result2.context.conversation_history.turns]}"
    )
    print(f"section_names = {section_names}")
    print(f"user_request = {prompt2.section('user_request').content}")
    print(f"system_instructions_present = {'system_instructions' in section_names}")
    print(f"conversation_history_present = {'conversation_history' in section_names}")
    print(f"retrieved_knowledge_present = {'retrieved_knowledge' in section_names}")
    print(f"user_request_present = {'user_request' in section_names}")
    print(f"first_question_in_history = {q1 in history_text}")
    print(f"first_answer_in_history = {result1.answer[:48] in history_text}")
    print(f"first_question_not_in_knowledge = {q1 not in knowledge_text}")
    print(
        "knowledge_contains_platform_fact = "
        f"{'Memovi is a self-hosted knowledge platform.' in knowledge_text}"
    )
    print(f"retrieved_knowledge_count = {len(result2.context.retrieved_knowledge)}")
    print(f"assistant_preview = {result2.answer[:180].replace(chr(10), ' ')}")

    assert len(history2.turns) == 2
    assert len(result2.context.conversation_history.turns) == 2
    assert result2.context.conversation_history.turns[0].content == q1
    assert result2.context.conversation_history.turns[1].content == result1.answer
    assert prompt2.section("user_request").content == q2
    assert section_names[:4] == [
        "system_instructions",
        "user_request",
        "conversation_history",
        "retrieved_knowledge",
    ]
    assert q1 in history_text
    assert "Memovi is a self-hosted knowledge platform." in knowledge_text
    assert q1 not in knowledge_text

    # --- Follow-up: What did I ask first? ---
    q3 = "What did I ask first?"
    history3 = conversations.load_history(conversation.id)
    result3 = reason.execute(
        ReasoningRequest.create(query=q3),
        conversation_history=history3,
    )
    prompt3 = builder.build(result3.context)
    history3_text = prompt3.section("conversation_history").content

    print("\n=== Follow-up: What did I ask first? ===")
    print(f"user = {q3}")
    print(f"history_turn_count = {len(history3.turns)}")
    print(
        "first_question_in_context = "
        f"{any(turn.content == q1 for turn in result3.context.conversation_history.turns)}"
    )
    print(f"first_question_in_prompt = {q1 in history3_text}")
    print(f"user_request = {prompt3.section('user_request').content}")
    print(f"section_names = {[section.name for section in prompt3.sections]}")
    print(f"assistant_preview = {result3.answer[:180].replace(chr(10), ' ')}")

    assert len(history3.turns) == 4
    assert any(turn.content == q1 for turn in result3.context.conversation_history.turns)
    assert q1 in history3_text
    assert prompt3.section("user_request").content == q3

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
