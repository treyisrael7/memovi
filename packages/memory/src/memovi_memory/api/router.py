from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_observability import timed_operation
from memovi_shared import WorkspaceId

from memovi_memory.api.dependencies import (
    get_active_workspace_id,
    get_get_knowledge,
    get_knowledge_dashboard,
    get_list_concepts,
    get_list_document_knowledge,
    get_list_knowledge,
    get_list_relationships,
)
from memovi_memory.api.schemas import (
    ChunkResponse,
    ConceptListResponse,
    ConceptResponse,
    KnowledgeDashboardResponse,
    KnowledgeDetailResponse,
    KnowledgeSummaryListResponse,
    KnowledgeSummaryResponse,
    RelationshipListResponse,
    RelationshipResponse,
)
from memovi_memory.application.dto import KnowledgeDto, KnowledgeSummaryDto
from memovi_memory.application.exceptions import KnowledgeItemNotFoundError
from memovi_memory.application.queries import (
    GetKnowledge,
    GetKnowledgeDashboard,
    ListConcepts,
    ListDocumentKnowledge,
    ListKnowledge,
    ListRelationships,
)

router = APIRouter(prefix="/memory", tags=["memory"])


def _summary_from_knowledge(knowledge: KnowledgeDto) -> KnowledgeSummaryResponse:
    summary = KnowledgeSummaryDto.from_knowledge(knowledge)
    return KnowledgeSummaryResponse(
        id=summary.id,
        workspace_id=summary.workspace_id,
        document_id=summary.document_id,
        document_version_id=summary.document_version_id,
        source_type=summary.source_type,
        mime_type=summary.mime_type,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        chunk_count=summary.chunk_count,
        summary=summary.summary,
        confidence=summary.confidence,
    )


def _detail_from_knowledge(knowledge: KnowledgeDto) -> KnowledgeDetailResponse:
    summary = KnowledgeSummaryDto.from_knowledge(knowledge)
    return KnowledgeDetailResponse(
        id=knowledge.id,
        workspace_id=knowledge.workspace_id,
        document_id=knowledge.document_id,
        document_version_id=knowledge.document_version_id,
        source_type=knowledge.source_type,
        mime_type=knowledge.mime_type,
        created_at=knowledge.created_at,
        updated_at=knowledge.updated_at,
        summary=summary.summary,
        confidence=None,
        chunks=[
            ChunkResponse(
                id=chunk.id,
                knowledge_item_id=chunk.knowledge_item_id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                created_at=chunk.created_at,
            )
            for chunk in knowledge.chunks
        ],
    )


def _matches_filters(
    item: KnowledgeDto,
    *,
    document_id: str | None,
    source_type: str | None,
    mime_type: str | None,
    entity_type: str | None,
) -> bool:
    if document_id is not None and item.document_id != document_id:
        return False
    if source_type is not None and item.source_type != source_type:
        return False
    if mime_type is not None and item.mime_type != mime_type:
        return False
    if entity_type is not None and item.source_type != entity_type and item.mime_type != entity_type:
        return False
    return True


@router.get(
    "/dashboard",
    response_model=KnowledgeDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Knowledge explorer dashboard",
    description=(
        "Return workspace-scoped counts for the Knowledge Explorer overview. "
        "Active workspace is resolved from X-Memovi-Workspace-Id or the Default Workspace."
    ),
)
def knowledge_dashboard(
    use_case: Annotated[GetKnowledgeDashboard, Depends(get_knowledge_dashboard)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> KnowledgeDashboardResponse:
    with timed_operation(
        "memory.dashboard",
        metric_name="memovi.memory.dashboard",
        attributes={"operation": "memory.dashboard"},
    ):
        dashboard = use_case.execute(workspace_id=workspace_id)
    return KnowledgeDashboardResponse(
        workspace_id=dashboard.workspace_id,
        knowledge_item_count=dashboard.knowledge_item_count,
        chunk_count=dashboard.chunk_count,
        source_document_count=dashboard.source_document_count,
        concept_count=dashboard.concept_count,
        relationship_count=dashboard.relationship_count,
        source_type_counts=dashboard.source_type_counts,
        mime_type_counts=dashboard.mime_type_counts,
    )


@router.get(
    "/concepts",
    response_model=ConceptListResponse,
    status_code=status.HTTP_200_OK,
    summary="List structural knowledge concepts",
    description=(
        "List structural concept groupings (source type and MIME type) derived from "
        "durable knowledge. These are inspection projections, not NLP-extracted topics."
    ),
)
def list_concepts(
    use_case: Annotated[ListConcepts, Depends(get_list_concepts)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ConceptListResponse:
    concepts = use_case.execute(workspace_id=workspace_id)
    items = [
        ConceptResponse(
            id=concept.id,
            kind=concept.kind,
            label=concept.label,
            knowledge_item_count=concept.knowledge_item_count,
            knowledge_item_ids=list(concept.knowledge_item_ids),
        )
        for concept in concepts
    ]
    return ConceptListResponse(items=items, count=len(items))


@router.get(
    "/relationships",
    response_model=RelationshipListResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge provenance relationships",
    description=(
        "List provenance relationships linking documents, knowledge items, and chunks. "
        "Optional filters narrow to a document or knowledge item."
    ),
)
def list_relationships(
    use_case: Annotated[ListRelationships, Depends(get_list_relationships)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    document_id: Annotated[
        str | None,
        Query(description="Restrict relationships to a source document."),
    ] = None,
    knowledge_item_id: Annotated[
        str | None,
        Query(description="Restrict relationships to a knowledge item."),
    ] = None,
) -> RelationshipListResponse:
    relationships = use_case.execute(
        workspace_id=workspace_id,
        document_id=document_id,
        knowledge_item_id=knowledge_item_id,
    )
    items = [
        RelationshipResponse(
            id=rel.id,
            relationship_type=rel.relationship_type,
            from_kind=rel.from_kind,
            from_id=rel.from_id,
            to_kind=rel.to_kind,
            to_id=rel.to_id,
            workspace_id=rel.workspace_id,
            document_id=rel.document_id,
            knowledge_item_id=rel.knowledge_item_id,
            created_at=rel.created_at,
        )
        for rel in relationships
    ]
    return RelationshipListResponse(items=items, count=len(items))


@router.get(
    "",
    response_model=KnowledgeSummaryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge entities",
    description=(
        "List inspectable knowledge items (entities) in the active workspace. "
        "Supports filters by document, source type, MIME type, and entity type "
        "(entity type matches source_type or mime_type until semantic entity extraction lands)."
    ),
)
def list_knowledge(
    use_case: Annotated[ListKnowledge, Depends(get_list_knowledge)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    document_id: Annotated[
        str | None,
        Query(description="Restrict to knowledge from a single document."),
    ] = None,
    source_type: Annotated[
        str | None,
        Query(description="Restrict to a document source type."),
    ] = None,
    mime_type: Annotated[
        str | None,
        Query(description="Restrict to a MIME type."),
    ] = None,
    entity_type: Annotated[
        str | None,
        Query(
            description=(
                "Restrict by entity type. Currently matches source_type or mime_type."
            ),
        ),
    ] = None,
) -> KnowledgeSummaryListResponse:
    with timed_operation(
        "memory.list",
        metric_name="memovi.memory.list",
        attributes={"operation": "memory.list"},
    ):
        knowledge_items = [
            item
            for item in use_case.execute(workspace_id=workspace_id)
            if _matches_filters(
                item,
                document_id=document_id,
                source_type=source_type,
                mime_type=mime_type,
                entity_type=entity_type,
            )
        ]
    items = [_summary_from_knowledge(item) for item in knowledge_items]
    return KnowledgeSummaryListResponse(items=items, count=len(items))


@router.get(
    "/by-document/{document_id}",
    response_model=KnowledgeSummaryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge for a document",
)
def list_document_knowledge(
    document_id: str,
    use_case: Annotated[ListDocumentKnowledge, Depends(get_list_document_knowledge)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> KnowledgeSummaryListResponse:
    knowledge_items = use_case.execute(document_id, workspace_id=workspace_id)
    items = [_summary_from_knowledge(item) for item in knowledge_items]
    return KnowledgeSummaryListResponse(items=items, count=len(items))


@router.get(
    "/{knowledge_item_id}",
    response_model=KnowledgeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get knowledge entity detail",
    description=(
        "Return a single knowledge item with chunks, source document reference, "
        "extraction timestamps, and confidence (null until extraction scores exist)."
    ),
    responses={
        200: {"description": "Knowledge item detail."},
        404: {"description": "Knowledge item was not found in the active workspace."},
    },
)
def get_knowledge(
    knowledge_item_id: str,
    use_case: Annotated[GetKnowledge, Depends(get_get_knowledge)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> KnowledgeDetailResponse:
    try:
        knowledge = use_case.execute(knowledge_item_id, workspace_id=workspace_id)
    except KnowledgeItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return _detail_from_knowledge(knowledge)
