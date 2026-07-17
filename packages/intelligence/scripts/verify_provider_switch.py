"""Live verification script: Reason -> ModelGateway -> configured provider.

Loads repo-root .env without printing secrets. Usage:
  uv run python packages/intelligence/scripts/verify_provider_switch.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "packages" / "intelligence" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing env file: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _run(label: str) -> None:
    from memovi_intelligence.application.commands import Reason
    from memovi_intelligence.application.services import (
        ContextAssembler,
        ModelGateway,
        PromptBuilder,
    )
    from memovi_intelligence.config import IntelligenceConfig
    from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
    from memovi_intelligence.domain.value_objects import Prompt, RetrievedKnowledge
    from memovi_intelligence.infrastructure import (
        OpenAIReasoningProvider,
        build_model_gateway,
        serialize_prompt_messages,
    )
    from memovi_intelligence.infrastructure.providers.fake_reasoning_provider import (
        FakeReasoningProvider,
    )

    class RecordingGateway:
        def __init__(self, gateway: ModelGateway) -> None:
            self._gateway = gateway
            self.execute_calls = 0
            self.resolved_provider_type: str | None = None

        def __getattr__(self, name: str) -> Any:
            return getattr(self._gateway, name)

        def execute(self, prompt: Prompt) -> ReasoningResult:
            self.execute_calls += 1
            provider = self._gateway._resolve_provider()
            self.resolved_provider_type = type(provider).__name__
            return self._gateway.execute(prompt)

    class StubRetriever:
        def __init__(self, items: tuple[RetrievedKnowledge, ...]) -> None:
            self._items = items

        def retrieve(
            self,
            request: ReasoningRequest,
            *,
            limit: int,
        ) -> tuple[RetrievedKnowledge, ...]:
            return self._items[:limit]

    knowledge = (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-knowledge",
            document_id="doc-principles",
            text="Knowledge is the product.",
            score=0.90,
            document_title="Principles",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-ai",
            document_id="doc-principles",
            text="AI is a consumer.",
            score=0.85,
            document_title="Principles",
        ),
    )

    config = IntelligenceConfig.from_env()
    gateway = RecordingGateway(build_model_gateway(config))
    retriever = StubRetriever(knowledge)
    assembler = ContextAssembler(knowledge_retriever=retriever)
    builder = PromptBuilder()
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        model_gateway=gateway,  # type: ignore[arg-type]
        prompt_builder=builder,
    )
    request = ReasoningRequest.create(query="What is Memovi?")
    prompt = builder.build(assembler.assemble(request))
    messages = serialize_prompt_messages(prompt)
    result = command.execute(request)

    print(f"=== {label} ===")
    print(f"config.provider = {config.provider}")
    print(f"config.model = {config.model}")
    print(f"reason_calls_gateway = {gateway.execute_calls == 1}")
    print(f"resolved_provider = {gateway.resolved_provider_type}")
    print(f"serialized_roles = {[message['role'] for message in messages]}")
    print(f"result.provider = {result.provider}")
    print(f"result.model = {result.metadata.get('model')}")
    print(f"result.execution_time = {result.execution_time}")
    print(f"result.duration = {result.metadata.get('duration')}")
    print(f"prompt_tokens = {result.metadata.get('prompt_tokens')}")
    print(f"completion_tokens = {result.metadata.get('completion_tokens')}")
    print(f"total_tokens = {result.metadata.get('total_tokens')}")
    print(f"citation_count = {len(result.citations)}")
    print(f"citations_match_prompt = {result.citations == prompt.citations}")
    print(f"answer_preview = {result.answer[:200].replace(chr(10), ' ')}")
    assert gateway.execute_calls == 1
    assert not hasattr(command, "_reasoning_provider")
    if config.provider == "openai":
        assert gateway.resolved_provider_type == OpenAIReasoningProvider.__name__
        assert result.provider == "openai"
        assert result.metadata["model"] == config.model
    else:
        assert gateway.resolved_provider_type == FakeReasoningProvider.__name__
        assert result.provider == "fake"
    assert result.citations == prompt.citations
    assert result.execution_time >= 0.0
    assert result.answer


def main() -> None:
    env_path = ROOT / ".env"
    _load_dotenv(env_path)
    # Force reload from current file values for switching runs.
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")
    provider = os.environ.get("INTELLIGENCE_PROVIDER", "fake")
    _run(f"provider={provider}")


if __name__ == "__main__":
    main()
