from api.app import create_app
from api.intelligence_integration import get_search_knowledge_retriever
from memovi_intelligence.api.dependencies import get_knowledge_retriever
from memovi_intelligence.infrastructure import FakeKnowledgeRetriever


def test_composition_root_wires_search_knowledge_retriever() -> None:
    app = create_app()

    assert app.dependency_overrides[get_knowledge_retriever] is get_search_knowledge_retriever
    assert not isinstance(
        getattr(app.state, "knowledge_retriever", None),
        FakeKnowledgeRetriever,
    )
