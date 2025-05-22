# Repository Guidelines for Codex

These instructions apply to all files in this repository.

Do not create new branches.

## Development workflow

- Use **Python 3.8+**. After modifying any `.py` files, run `python -m py_compile` on each updated file to ensure there are no syntax errors.
- If your changes affect large components or introduce new features, prefer creating new files instead of heavily modifying existing ones. Update `changelog.md` with a summary of the changes.
- When architectural aspects change, update `DeepSOC架构文档.md` accordingly.
- If `.env` variables are modified, mirror the updates in `sample.env`.
- Tests belong in the `test` directory. Temporary or helper scripts go into the `tools` directory and should include basic usage instructions.

## Running the project

To initialize and start all services for development:

```bash
python main.py -init   # first-time database setup
python tools/run_all_agents.py  # launch web service and all agent roles
```

Refer to `README.md` for more details.
