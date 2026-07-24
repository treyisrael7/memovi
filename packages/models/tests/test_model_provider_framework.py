from dataclasses import FrozenInstanceError

import pytest
from memovi_models import (
    PROVIDER_FAKE,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    UNSUPPORTED_CAPABILITY_ERROR,
    FakeModelProvider,
    InvalidModelError,
    ModelCapabilities,
    ModelRegistry,
    ModelRequest,
    ProviderConfiguration,
    ProviderHealth,
    UnknownProviderError,
)


def _registry_with(*providers: FakeModelProvider) -> ModelRegistry:
    registry = ModelRegistry()
    for provider in providers:
        registry.register(provider)
    return registry


def test_model_registry_register_list_lookup_and_capabilities() -> None:
    fake = FakeModelProvider()
    ollama = FakeModelProvider(provider_id=PROVIDER_OLLAMA, model_id="llama3")
    registry = _registry_with(fake, ollama)

    assert registry.list_providers() == (PROVIDER_FAKE, PROVIDER_OLLAMA)
    assert registry.contains(PROVIDER_FAKE)
    assert registry.get(PROVIDER_FAKE) is fake
    assert {model.id for model in registry.list_models()} == {"fake-chat", "llama3"}
    assert registry.list_models(PROVIDER_OLLAMA)[0].id == "llama3"
    assert registry.capabilities(PROVIDER_FAKE).chat is True
    assert registry.capabilities(PROVIDER_FAKE).streaming is False
    assert registry.get_model("llama3").provider_id == PROVIDER_OLLAMA


def test_model_registry_rejects_duplicate_and_unknown() -> None:
    registry = _registry_with(FakeModelProvider())

    with pytest.raises(InvalidModelError, match="already registered"):
        registry.register(FakeModelProvider())
    with pytest.raises(UnknownProviderError, match="Unknown provider"):
        registry.get("missing")


def test_fake_provider_complete_success_and_streaming_unsupported() -> None:
    registry = _registry_with(FakeModelProvider(default_reply="ack"))
    provider = registry.get(PROVIDER_FAKE)
    request = ModelRequest.create(
        model_id="fake-chat",
        messages=[("user", "hello")],
    )

    result = provider.complete(request)

    assert result.success is True
    assert result.provider_id == PROVIDER_FAKE
    assert result.content == "ack:hello"
    assert result.usage is not None
    assert result.metadata["fake"] is True

    streamed = provider.complete(
        ModelRequest.create(
            model_id="fake-chat",
            messages=[("user", "hello")],
            stream=True,
        ),
    )
    assert streamed.success is False
    assert streamed.error is not None
    assert streamed.error.code == UNSUPPORTED_CAPABILITY_ERROR


def test_health_checks_across_providers() -> None:
    healthy = FakeModelProvider(provider_id="alpha", model_id="a")
    unhealthy = FakeModelProvider(provider_id="beta", model_id="b", healthy=False)
    disabled = FakeModelProvider(provider_id="gamma", model_id="c", enabled=False)
    registry = _registry_with(healthy, unhealthy, disabled)

    statuses = {item.provider_id: item.status for item in registry.health_all()}
    assert statuses == {
        "alpha": "healthy",
        "beta": "unhealthy",
        "gamma": "unavailable",
    }
    assert registry.health("alpha").is_healthy is True


def test_provider_configuration_and_capabilities_contracts() -> None:
    config = ProviderConfiguration(
        provider_id=PROVIDER_OPENAI,
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        base_url="https://api.openai.com/v1",
        extra={"organization": "org"},
    )
    capabilities = ModelCapabilities(chat=True, tool_calling=True, vision=True)

    assert config.provider_id == "openai"
    assert config.api_key_env == "OPENAI_API_KEY"
    assert "api_key" not in config.extra
    assert capabilities.enabled_names() == ("chat", "tool_calling", "vision")
    assert capabilities.supports("tool_calling") is True
    assert capabilities.merge(ModelCapabilities(embeddings=True)).embeddings is True

    with pytest.raises(InvalidModelError):
        ProviderConfiguration(provider_id="", enabled=True)
    with pytest.raises(InvalidModelError):
        ModelCapabilities().supports("telepathy")


def test_value_objects_are_immutable() -> None:
    capabilities = ModelCapabilities(chat=True)
    health = ProviderHealth(provider_id="fake", status="healthy", message="ok")
    request = ModelRequest.create(model_id="fake-chat", messages=[("user", "hi")])

    with pytest.raises(FrozenInstanceError):
        capabilities.chat = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        health.status = "unhealthy"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.metadata["x"] = 1  # type: ignore[index]


def test_integration_multiple_providers_through_registry() -> None:
    registry = ModelRegistry()
    registry.register(FakeModelProvider(provider_id=PROVIDER_FAKE, model_id="fake-chat"))
    registry.register(FakeModelProvider(provider_id=PROVIDER_OLLAMA, model_id="llama3"))

    openai_shaped = FakeModelProvider(provider_id=PROVIDER_OPENAI, model_id="gpt-fake")
    registry.register(openai_shaped)

    assert set(registry.list_providers()) == {PROVIDER_FAKE, PROVIDER_OLLAMA, PROVIDER_OPENAI}
    assert len(registry.list_models()) == 3

    for provider_id in registry.list_providers():
        assert registry.capabilities(provider_id).supports("chat")
        health = registry.health(provider_id)
        assert health.provider_id == provider_id
        assert health.status in {"healthy", "unhealthy", "unknown", "unavailable"}

    response = registry.get(PROVIDER_OLLAMA).complete(
        ModelRequest.create(model_id="llama3", messages=[("system", "s"), ("user", "ping")]),
    )
    assert response.success is True
    assert response.content == "fake-response:ping"
    assert response.provider_id == PROVIDER_OLLAMA
