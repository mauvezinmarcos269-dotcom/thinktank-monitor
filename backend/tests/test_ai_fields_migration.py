import importlib.util
from pathlib import Path
from unittest.mock import Mock, call


def _load_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/e038b9014347_add_ai_fields.py"
    )
    spec = importlib.util.spec_from_file_location("ai_fields_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_upgrade_adds_all_ai_columns_to_clean_schema(monkeypatch):
    migration = _load_migration()
    operation = Mock()
    monkeypatch.setattr(migration, "op", operation)
    monkeypatch.setattr(migration, "_report_columns", lambda: {"id"})

    migration.upgrade()

    added_columns = {
        args[1].name for args, _kwargs in operation.add_column.call_args_list
    }
    assert added_columns == {
        "translation",
        "summary",
        "commentary",
        "ai_generated_at",
        "ai_status",
    }
    operation.alter_column.assert_not_called()


def test_upgrade_repairs_existing_nullable_ai_status(monkeypatch):
    migration = _load_migration()
    operation = Mock()
    monkeypatch.setattr(migration, "op", operation)
    monkeypatch.setattr(
        migration,
        "_report_columns",
        lambda: {
            "id",
            "translation",
            "summary",
            "commentary",
            "ai_generated_at",
            "ai_status",
        },
    )

    migration.upgrade()

    operation.add_column.assert_not_called()
    operation.execute.assert_called_once_with(
        "UPDATE reports SET ai_status = 'pending' WHERE ai_status IS NULL"
    )
    assert operation.alter_column.call_args.kwargs["nullable"] is False
    assert operation.alter_column.call_args.kwargs["server_default"] == "pending"


def test_downgrade_removes_only_present_ai_columns(monkeypatch):
    migration = _load_migration()
    operation = Mock()
    monkeypatch.setattr(migration, "op", operation)
    monkeypatch.setattr(
        migration,
        "_report_columns",
        lambda: {"id", "translation", "ai_status"},
    )

    migration.downgrade()

    assert operation.drop_column.call_args_list == [
        call("reports", "ai_status"),
        call("reports", "translation"),
    ]
