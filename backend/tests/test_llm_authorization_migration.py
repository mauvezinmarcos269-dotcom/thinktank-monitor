import importlib.util
from pathlib import Path

import sqlalchemy as sa

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_authorization_migration_does_not_grant_historical_documents():
    path = Path(__file__).parents[1] / "alembic/versions/c8e4a6d91203_add_llm_authorizations.py"
    spec = importlib.util.spec_from_file_location("authorization_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    for name in ("users", "reports", "crawl_candidates"):
        sa.Table(name, metadata, sa.Column("id", sa.Integer, primary_key=True))
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(metadata.tables["reports"].insert().values(id=1))
        connection.execute(metadata.tables["crawl_candidates"].insert().values(id=1))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            columns = {
                column["name"] for column in sa.inspect(connection).get_columns("crawl_candidates")
            }
            assert columns == {"id", "document_hash", "content_length"}
            assert connection.scalar(sa.text("SELECT count(*) FROM llm_authorizations")) == 0
            assert connection.scalar(sa.text("SELECT count(*) FROM reports")) == 1
            assert (
                connection.scalar(sa.text("SELECT document_hash FROM crawl_candidates WHERE id=1"))
                is None
            )
            migration.downgrade()
            assert "llm_authorizations" not in sa.inspect(connection).get_table_names()
            assert {
                column["name"] for column in sa.inspect(connection).get_columns("crawl_candidates")
            } == {"id"}
            assert connection.scalar(sa.text("SELECT count(*) FROM reports")) == 1
    engine.dispose()
