import pytest

from saint_elmo_backend.db import testing


def test_to_test_database_url_appends_test_suffix():
    url = testing.to_test_database_url(
        "postgresql+asyncpg://app_migrator:p%40ss@localhost:5432/saint_elmo"
    )

    assert url == "postgresql+asyncpg://app_migrator:p%40ss@localhost:5432/saint_elmo_test"


def test_to_test_database_url_keeps_existing_test_database():
    url = testing.to_test_database_url(
        "postgresql+asyncpg://app_migrator:password@localhost:5432/saint_elmo_test"
    )

    assert url == "postgresql+asyncpg://app_migrator:password@localhost:5432/saint_elmo_test"


@pytest.mark.parametrize("database", ["saint_elmo", "saint_elmo_testing", "test"])
async def test_truncate_all_refuses_non_test_database(database):
    url = f"postgresql+asyncpg://app_migrator:password@localhost:5432/{database}"

    with pytest.raises(testing.NotATestDatabase):
        await testing.truncate_all(url)
