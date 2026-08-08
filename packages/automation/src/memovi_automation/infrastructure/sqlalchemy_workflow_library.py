"""Durable SQLAlchemy workflow definition library."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session as OrmSession

from memovi_automation.domain.exceptions import InvalidWorkflowError, UnknownWorkflowError
from memovi_automation.domain.value_objects.workflow import WorkflowDefinition
from memovi_automation.infrastructure.in_memory_workflow_library import built_in_workflows
from memovi_automation.infrastructure.persistence.models import WorkflowDefinitionRecord
from memovi_automation.infrastructure.workflow_codec import (
    deserialize_definition,
    serialize_definition,
    serialize_step,
    serialize_variable,
)

SessionFactory = Callable[[], OrmSession]


def _is_builtin(definition: WorkflowDefinition) -> bool:
    return bool(definition.metadata.get("builtin"))


class SqlAlchemyWorkflowLibrary:
    """Postgres/SQLite-backed WorkflowLibrary with built-in seeding."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        seed_built_ins: bool = True,
    ) -> None:
        self._session_factory = session_factory
        if seed_built_ins:
            self.ensure_built_ins()

    def ensure_built_ins(self) -> None:
        """Seed built-in definitions without overwriting customized rows."""
        session = self._session_factory()
        try:
            for definition in built_in_workflows():
                existing = session.get(WorkflowDefinitionRecord, definition.workflow_id)
                if existing is not None:
                    continue
                session.add(self._to_record(definition))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, workflow_id: str) -> WorkflowDefinition:
        key = workflow_id.strip()
        session = self._session_factory()
        try:
            record = session.get(WorkflowDefinitionRecord, key)
            if record is None:
                raise UnknownWorkflowError(
                    f"Unknown workflow '{workflow_id}'.",
                    workflow_id=workflow_id,
                )
            return self._to_domain(record)
        finally:
            session.close()

    def list(self) -> tuple[WorkflowDefinition, ...]:
        session = self._session_factory()
        try:
            records = (
                session.query(WorkflowDefinitionRecord)
                .order_by(WorkflowDefinitionRecord.name.asc())
                .all()
            )
            return tuple(self._to_domain(record) for record in records)
        finally:
            session.close()

    def register(self, definition: WorkflowDefinition) -> None:
        session = self._session_factory()
        try:
            record = session.get(WorkflowDefinitionRecord, definition.workflow_id)
            if record is None:
                session.add(self._to_record(definition))
            else:
                self._apply(record, definition, bump_version=False)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        session = self._session_factory()
        try:
            existing = session.get(WorkflowDefinitionRecord, definition.workflow_id)
            if existing is not None:
                raise InvalidWorkflowError(
                    f"Workflow '{definition.workflow_id}' already exists.",
                    code="workflow_exists",
                    details={"workflow_id": definition.workflow_id},
                )
            session.add(self._to_record(definition))
            session.commit()
            return definition
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        session = self._session_factory()
        try:
            record = session.get(WorkflowDefinitionRecord, definition.workflow_id)
            if record is None:
                raise UnknownWorkflowError(
                    f"Unknown workflow '{definition.workflow_id}'.",
                    workflow_id=definition.workflow_id,
                )
            current = self._to_domain(record)
            if _is_builtin(current):
                raise InvalidWorkflowError(
                    f"Built-in workflow '{definition.workflow_id}' cannot be updated.",
                    code="builtin_immutable",
                    details={"workflow_id": definition.workflow_id},
                )
            updated = WorkflowDefinition(
                workflow_id=definition.workflow_id,
                name=definition.name,
                description=definition.description,
                steps=definition.steps,
                variables=definition.variables,
                expected_outputs=definition.expected_outputs,
                required_capabilities=definition.required_capabilities,
                metadata=definition.metadata,
                version=max(current.version + 1, definition.version),
                workspace_id=(
                    definition.workspace_id
                    if definition.workspace_id is not None
                    else current.workspace_id
                ),
                created_at=current.created_at,
                updated_at=datetime.now(UTC),
            )
            self._apply(record, updated, bump_version=False)
            session.commit()
            return updated
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, workflow_id: str) -> None:
        key = workflow_id.strip()
        session = self._session_factory()
        try:
            record = session.get(WorkflowDefinitionRecord, key)
            if record is None:
                raise UnknownWorkflowError(
                    f"Unknown workflow '{workflow_id}'.",
                    workflow_id=workflow_id,
                )
            current = self._to_domain(record)
            if _is_builtin(current):
                raise InvalidWorkflowError(
                    f"Built-in workflow '{workflow_id}' cannot be deleted.",
                    code="builtin_immutable",
                    details={"workflow_id": workflow_id},
                )
            session.delete(record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def duplicate(
        self,
        workflow_id: str,
        *,
        new_workflow_id: str | None = None,
        name: str | None = None,
    ) -> WorkflowDefinition:
        source = self.get(workflow_id)
        new_id = (new_workflow_id or f"{source.workflow_id}-copy-{uuid4().hex[:8]}").strip()
        copy = WorkflowDefinition(
            workflow_id=new_id,
            name=(name or f"Copy of {source.name}").strip(),
            description=source.description,
            steps=source.steps,
            variables=source.variables,
            expected_outputs=source.expected_outputs,
            required_capabilities=source.required_capabilities,
            metadata={k: v for k, v in source.metadata.items() if k != "builtin"},
            version=1,
            workspace_id=source.workspace_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return self.create(copy)

    def _to_record(self, definition: WorkflowDefinition) -> WorkflowDefinitionRecord:
        payload = serialize_definition(definition)
        return WorkflowDefinitionRecord(
            workflow_id=definition.workflow_id,
            workspace_id=definition.workspace_id,
            name=definition.name,
            description=definition.description,
            version=definition.version,
            steps=list(payload["steps"]),  # type: ignore[arg-type]
            variables=list(payload["variables"]),  # type: ignore[arg-type]
            expected_outputs=list(definition.expected_outputs),
            required_capabilities=list(definition.required_capabilities),
            metadata_json=dict(definition.metadata),
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )

    def _apply(
        self,
        record: WorkflowDefinitionRecord,
        definition: WorkflowDefinition,
        *,
        bump_version: bool,
    ) -> None:
        record.workspace_id = definition.workspace_id
        record.name = definition.name
        record.description = definition.description
        record.version = (
            record.version + 1 if bump_version else definition.version
        )
        record.steps = [serialize_step(step) for step in definition.steps]  # type: ignore[assignment]
        record.variables = [serialize_variable(variable) for variable in definition.variables]  # type: ignore[assignment]
        record.expected_outputs = list(definition.expected_outputs)
        record.required_capabilities = list(definition.required_capabilities)
        record.metadata_json = dict(definition.metadata)
        record.updated_at = definition.updated_at

    def _to_domain(self, record: WorkflowDefinitionRecord) -> WorkflowDefinition:
        return deserialize_definition(
            {
                "workflow_id": record.workflow_id,
                "name": record.name,
                "description": record.description,
                "version": record.version,
                "workspace_id": record.workspace_id,
                "steps": record.steps or [],
                "variables": record.variables or [],
                "expected_outputs": record.expected_outputs or [],
                "required_capabilities": record.required_capabilities or [],
                "metadata": record.metadata_json or {},
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )
