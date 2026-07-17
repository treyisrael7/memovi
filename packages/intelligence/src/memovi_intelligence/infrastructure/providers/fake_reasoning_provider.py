from memovi_intelligence.domain.entities import ReasoningResult
from memovi_intelligence.domain.exceptions import InvalidPromptError
from memovi_intelligence.domain.value_objects import Prompt


class FakeReasoningProvider:
    """Deterministic reasoning provider for tests and local wiring.

    Consumes provider-agnostic Prompt objects and produces stable answers without
    AI or network calls.
    """

    PROVIDER_NAME = "fake"
    EXECUTION_TIME = 0.0

    def reason(self, prompt: Prompt) -> ReasoningResult:
        if not prompt.citations:
            raise InvalidPromptError("Cannot reason over a prompt without citations.")

        knowledge_section = prompt.section("retrieved_knowledge")
        answer = f"Answer for '{prompt.query}': {knowledge_section.content}"

        return ReasoningResult.create(
            answer=answer,
            citations=prompt.citations,
            metadata={
                "query": prompt.query,
                "chunk_count": len(prompt.citations),
                "document_count": len(prompt.context.assembled_documents),
                "estimated_token_count": prompt.context.estimated_token_count,
                "section_count": len(prompt.sections),
                "message_count": len(prompt.messages),
            },
            provider=self.PROVIDER_NAME,
            execution_time=self.EXECUTION_TIME,
            context=prompt.context,
        )
