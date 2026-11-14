# Saint Elmo backend

## Tests

```sh
cp .env.example .env          # once
docker compose up -d db
uv run pytest
```

Unit tests need nothing else. Integration tests (those using the `client`, `session`,
`clean_db` or `reference_data` fixtures from `conftest.py`) run against a separate
`<POSTGRES_DB>_test` database on the compose Postgres, e.g. `saint_elmo_test`. It is
created and migrated to head automatically on first use, and truncated before each
test, so the seeded dev database is never touched.

- `reference_data` seeds only the GS1 code lists. Insert the products a test needs
  with `catalog/tests/factories.py`, and buyer organisations and users with
  `accounts/tests/factories.py`.
