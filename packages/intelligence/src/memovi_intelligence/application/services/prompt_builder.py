from memovi_intelligence.domain.entities import ReasoningContext
from memovi_intelligence.domain.exceptions import InvalidPromptError
from memovi_intelligence.domain.value_objects import (
    Citation,
    Prompt,
    PromptMessage,
    PromptRole,
    PromptSection,
)

SYSTEM_INSTRUCTIONS = (
    "You are Memovi's reasoning assistant. "
    "Answer using only the retrieved knowledge provided in this prompt. "
    "If the knowledge is insufficient, say so clearly. "
    "Preserve provenance by referring to citation identifiers when relevant."
)

SECTION_SYSTEM_INSTRUCTIONS = "system_instructions"
SECTION_USER_REQUEST = "user_request"
SECTION_RETRIEVED_KNOWLEDGE = "retrieved_knowledge"
SECTION_CITATIONS = "citations"
SECTION_METADATA = "metadata"


class PromptBuilder:
    """Transforms ReasoningContext into a deterministic, provider-agnostic Prompt."""

    def build(self, context: ReasoningContext) -> Prompt:
        if context.is_empty:
            raise InvalidPromptError("Cannot build a prompt from an empty reasoning context.")

        citations = _citations_from_context(context)
        sections = (
            PromptSection(
                name=SECTION_SYSTEM_INSTRUCTIONS,
                content=SYSTEM_INSTRUCTIONS,
                order=0,
            ),
            PromptSection(
                name=SECTION_USER_REQUEST,
                content=context.query,
                order=1,
            ),
            PromptSection(
                name=SECTION_RETRIEVED_KNOWLEDGE,
                content=_format_retrieved_knowledge(context),
                order=2,
            ),
            PromptSection(
                name=SECTION_CITATIONS,
                content=_format_citations(citations),
                order=3,
            ),
            PromptSection(
                name=SECTION_METADATA,
                content=_format_metadata(context),
                order=4,
            ),
        )
        messages = (
            PromptMessage(role=PromptRole.SYSTEM, content=sections[0].content),
            PromptMessage(
                role=PromptRole.USER,
                content=_format_user_message(sections[1:]),
            ),
        )
        return Prompt(
            sections=sections,
            messages=messages,
            citations=citations,
            context=context,
        )


def _citations_from_context(context: ReasoningContext) -> tuple[Citation, ...]:
    return tuple(
        Citation(
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            document_title=item.document_title,
            score=item.score,
        )
        for item in context.retrieved_knowledge
    )


def _format_retrieved_knowledge(context: ReasoningContext) -> str:
    blocks: list[str] = []
    for index, item in enumerate(context.retrieved_knowledge, start=1):
        title = item.document_title or item.document_id
        header = (
            f"[{index}] {title} "
            f"(document_id={item.document_id}, chunk_id={item.chunk_id}, score={item.score})"
        )
        blocks.append(f"{header}\n{item.text}")
    return "\n\n".join(blocks)


def _format_citations(citations: tuple[Citation, ...]) -> str:
    lines: list[str] = []
    for index, citation in enumerate(citations, start=1):
        title = citation.document_title or citation.document_id
        score = "" if citation.score is None else f", score={citation.score}"
        lines.append(
            f"[{index}] {title} "
            f"(document_id={citation.document_id}, chunk_id={citation.chunk_id}{score})"
        )
    return "\n".join(lines)


def _format_metadata(context: ReasoningContext) -> str:
    metadata = context.metadata
    return "\n".join(
        (
            f"request_id={context.request.id.value}",
            f"retrieved_count={metadata.retrieved_count}",
            f"retained_chunk_count={metadata.retained_chunk_count}",
            f"retained_document_count={metadata.retained_document_count}",
            f"truncated={str(metadata.truncated).lower()}",
            f"duplicate_chunks_removed={metadata.duplicate_chunks_removed}",
            f"duplicate_documents_skipped={metadata.duplicate_documents_skipped}",
            f"estimated_token_count={context.estimated_token_count}",
        )
    )


def _format_user_message(sections: tuple[PromptSection, ...]) -> str:
    parts: list[str] = []
    for section in sections:
        heading = section.name.replace("_", " ").upper()
        parts.append(f"## {heading}\n{section.content}")
    return "\n\n".join(parts)
