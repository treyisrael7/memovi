"""Milestone 19 acceptance verification for the conversation experience.

Exercises the same HTTP contracts the desktop client uses:
1. Multi-turn conversation
2. History persistence across a new client session (reopen equivalent)
3. Workspace isolation
4. Model/provider selection on requests
5. Streaming interrupt recovery
"""

from __future__ import annotations

import sys
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import (
    get_conversation_repository,
    get_intelligence_config,
    get_knowledge_retriever,
    get_model_gateway,
)
from memovi_intelligence.api.router import router
from memovi_intelligence.application.services import ModelGateway
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.infrastructure import (
    FakeKnowledgeRetriever,
    FakeReasoningProvider,
    InMemoryConversationRepository,
)

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
PASS = 0
FAIL = 0


def _ok(label: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {label}")


def _fail(label: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL  {label}: {detail}")


def _build_conversation_app() -> FastAPI:
    repository = InMemoryConversationRepository()
    config = IntelligenceConfig(provider="fake", model="fake-reasoning-v1")
    retriever = FakeKnowledgeRetriever()
    gateway = ModelGateway(
        providers={"fake": FakeReasoningProvider()},
        config=config,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    app.dependency_overrides[get_intelligence_config] = lambda: config
    app.dependency_overrides[get_knowledge_retriever] = lambda: retriever
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    # Keep repository on app.state so reopen uses the same store.
    app.state.conversation_repository = repository
    return app


def step_1_multi_turn(client: TestClient) -> str:
    print("\n1. Create conversation and exchange several messages")
    created = client.post("/conversations")
    if created.status_code != 201:
        _fail("create conversation", f"status={created.status_code}")
        return ""
    conversation_id = created.json()["conversation_id"]
    _ok(f"created conversation {conversation_id}")

    messages = [
        "What is Memovi?",
        "Introduce yourself briefly.",
        "What is Memovi again?",
    ]
    for index, message in enumerate(messages, start=1):
        response = client.post(
            f"/conversations/{conversation_id}/messages",
            json={"message": message},
        )
        if response.status_code != 200:
            _fail(
                f"send message {index}",
                f"status={response.status_code} body={response.text}",
            )
            return conversation_id
        payload = response.json()
        if not payload.get("assistant_message"):
            _fail(f"send message {index}", "missing assistant_message")
            return conversation_id
        _ok(f"exchange {index}: assistant reply " f"({payload['provider']}/{payload['model']})")

    history = client.get(f"/conversations/{conversation_id}/messages")
    if history.status_code != 200:
        _fail("load history", f"status={history.status_code}")
        return conversation_id
    turns = history.json()["messages"]
    if len(turns) != 6:
        _fail("history length", f"expected 6 turns, got {len(turns)}")
    else:
        _ok("history contains 6 turns (3 user + 3 assistant)")
    return conversation_id


def step_2_persistence(app: FastAPI, conversation_id: str) -> None:
    print("\n2. Close/reopen equivalent: new client session loads persisted history")
    with TestClient(app, base_url="https://testserver") as client:
        listed = client.get("/conversations")
        if listed.status_code != 200:
            _fail("list after reopen", f"status={listed.status_code}")
            return
        ids = [item["conversation_id"] for item in listed.json()["conversations"]]
        if conversation_id not in ids:
            _fail("conversation still listed", f"ids={ids}")
            return
        _ok("conversation still listed after new client session")

        history = client.get(f"/conversations/{conversation_id}/messages")
        if history.status_code != 200:
            _fail("history after reopen", f"status={history.status_code}")
            return
        turns = history.json()["messages"]
        if len(turns) != 6:
            _fail("persisted history length", f"expected 6, got {len(turns)}")
            return
        if turns[0]["role"] != "user" or turns[0]["content"] != "What is Memovi?":
            _fail("persisted first turn", str(turns[0]))
            return
        _ok("full conversation history persisted across reopen")


def step_3_workspace_isolation(client: TestClient) -> None:
    print("\n3. Workspace switching isolates conversations")
    workspace_a = str(uuid4())
    workspace_b = str(uuid4())
    headers_a = {WORKSPACE_HEADER: workspace_a}
    headers_b = {WORKSPACE_HEADER: workspace_b}

    create_a = client.post("/conversations", headers=headers_a)
    create_b = client.post("/conversations", headers=headers_b)
    if create_a.status_code != 201 or create_b.status_code != 201:
        _fail(
            "create in workspaces",
            f"a={create_a.status_code} b={create_b.status_code}",
        )
        return
    id_a = create_a.json()["conversation_id"]
    id_b = create_b.json()["conversation_id"]
    _ok("created one conversation per workspace")

    send_a = client.post(
        f"/conversations/{id_a}/messages",
        headers=headers_a,
        json={"message": "What is Memovi?"},
    )
    if send_a.status_code != 200:
        _fail("send in workspace A", f"status={send_a.status_code} body={send_a.text}")
        return
    _ok("sent message in workspace A")

    ids_a = {
        item["conversation_id"]
        for item in client.get("/conversations", headers=headers_a).json()["conversations"]
    }
    ids_b = {
        item["conversation_id"]
        for item in client.get("/conversations", headers=headers_b).json()["conversations"]
    }

    if id_a not in ids_a or id_b in ids_a:
        _fail("workspace A list isolation", f"ids_a={ids_a}")
    else:
        _ok("workspace A list contains only its conversation")

    if id_b not in ids_b or id_a in ids_b:
        _fail("workspace B list isolation", f"ids_b={ids_b}")
    else:
        _ok("workspace B list contains only its conversation")

    cross = client.get(f"/conversations/{id_a}", headers=headers_b)
    if cross.status_code != 404:
        _fail("cross-workspace get", f"expected 404, got {cross.status_code}")
    else:
        _ok("workspace B cannot read workspace A conversation")


def step_4_model_selection(client: TestClient) -> None:
    print("\n4. Active model selection is reflected in requests")
    models = client.get("/conversations/models")
    if models.status_code != 200:
        _fail("list models", f"status={models.status_code}")
        return
    payload = models.json()
    if payload["default_provider"] != "fake":
        _fail("default provider", str(payload))
        return
    _ok(f"models endpoint: default {payload['default_provider']}/{payload['default_model']}")

    created = client.post("/conversations").json()["conversation_id"]
    selected_model = "custom-fake-model"
    response = client.post(
        f"/conversations/{created}/messages",
        json={
            "message": "What is Memovi?",
            "provider": "fake",
            "model": selected_model,
        },
    )
    if response.status_code != 200:
        _fail(
            "send with model override",
            f"status={response.status_code} body={response.text}",
        )
        return
    body = response.json()
    if body.get("provider") != "fake":
        _fail("response provider", str(body.get("provider")))
    else:
        _ok("response provider is fake")
    if body.get("model") != selected_model:
        _fail("response model", f"expected {selected_model}, got {body.get('model')}")
    else:
        _ok(f"response model reflects selection ({selected_model})")
    if body["execution"]["metrics"]["model"] != selected_model:
        _fail("execution metrics model", str(body["execution"]["metrics"]))
    else:
        _ok("execution metrics model matches selected model")


def step_5_stream_interrupt(client: TestClient) -> None:
    print("\n5. Interrupt streaming and recover cleanly")
    created = client.post("/conversations").json()["conversation_id"]

    with client.stream(
        "POST",
        f"/conversations/{created}/messages/stream",
        json={"message": "What is Memovi?"},
    ) as response:
        if response.status_code != 200:
            _fail("open stream", f"status={response.status_code}")
            return
        buffered = ""
        for chunk in response.iter_text():
            buffered += chunk
            if "event: token" in buffered:
                break
        if "event: token" not in buffered:
            _fail("first stream event", repr(buffered[:200]))
            return
        _ok("received streaming token before interrupt")
        # Context exit closes the connection (desktop Stop / AbortController).

    history = client.get(f"/conversations/{created}/messages")
    if history.status_code != 200:
        _fail("history after interrupt", f"status={history.status_code}")
        return
    turns = history.json()["messages"]
    if not turns or turns[0]["role"] != "user":
        _fail("user turn after interrupt", str(turns))
        return
    _ok(f"history recoverable after interrupt ({len(turns)} turn(s))")

    # Desktop Retry: same user content against a conversation that may already
    # have that user turn recorded. Prefer a clean follow-up send for recovery.
    recovery = client.post(
        f"/conversations/{created}/messages",
        json={"message": "Introduce yourself briefly."},
    )
    if recovery.status_code != 200:
        _fail("recovery send", f"status={recovery.status_code} body={recovery.text}")
        return
    _ok("follow-up send succeeds after interrupt (UI recovery)")

    final_history = client.get(f"/conversations/{created}/messages").json()["messages"]
    if len(final_history) < 2:
        _fail("post-recovery history", f"turns={len(final_history)}")
    else:
        _ok(f"conversation usable after interrupt ({len(final_history)} turns)")


def main() -> int:
    print("Milestone 19 — Conversation Experience verification")
    app = _build_conversation_app()

    with TestClient(app, base_url="https://testserver") as client:
        conversation_id = step_1_multi_turn(client)
        if not conversation_id:
            print("\nAborting early due to step 1 failure.")
            return 1
        step_3_workspace_isolation(client)
        step_4_model_selection(client)
        step_5_stream_interrupt(client)

    step_2_persistence(app, conversation_id)

    print(f"\nSummary: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
