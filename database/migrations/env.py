"""Alembic environment.

Loads SQLAlchemy DeclarativeBase modules without importing package root
``__init__`` modules. Those package inits eagerly load application/domain
code and break under Python < 3.14 (forward-reference annotations).
Migrations only need table metadata.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.orm import DeclarativeBase

ROOT_DIR = Path(__file__).resolve().parents[2]


def _ensure_package(name: str, path: Path) -> None:
    """Register a package stub so submodule loads skip heavy package __init__."""
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


def _load_declarative_base(*, src_root: Path, import_root: str) -> type[DeclarativeBase]:
    """Import ``…infrastructure.persistence.models.Base`` without package side effects."""
    parts = import_root.split(".")
    for index in range(len(parts)):
        package_name = ".".join(parts[: index + 1])
        package_path = src_root.joinpath(*parts[: index + 1])
        _ensure_package(package_name, package_path)

    for suffix in ("infrastructure", "infrastructure.persistence"):
        package_name = f"{import_root}.{suffix}"
        package_path = src_root.joinpath(*parts, *suffix.split("."))
        _ensure_package(package_name, package_path)

    models_path = src_root.joinpath(*parts, "infrastructure", "persistence", "models.py")
    module_name = f"{import_root}.infrastructure.persistence.models"
    if module_name in sys.modules:
        return sys.modules[module_name].Base  # type: ignore[no-any-return]

    spec = importlib.util.spec_from_file_location(module_name, models_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load migration models from {models_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.Base  # type: ignore[no-any-return]


AuthBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "auth" / "src",
    import_root="auth",
)
AutomationBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "automation" / "src",
    import_root="memovi_automation",
)
DocumentsBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "documents" / "src",
    import_root="documents",
)
IntelligenceBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "intelligence" / "src",
    import_root="memovi_intelligence",
)
MemoryBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "memory" / "src",
    import_root="memovi_memory",
)
SearchBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "search" / "src",
    import_root="memovi_search",
)
WorkspaceBase = _load_declarative_base(
    src_root=ROOT_DIR / "packages" / "workspace" / "src",
    import_root="memovi_workspace",
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [
    AuthBase.metadata,
    AutomationBase.metadata,
    DocumentsBase.metadata,
    IntelligenceBase.metadata,
    MemoryBase.metadata,
    SearchBase.metadata,
    WorkspaceBase.metadata,
]


def database_url() -> str:
    from memovi_config.settings.database import DatabaseSettings

    return DatabaseSettings.from_environ(os.environ).url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
