# Track Metadata Builder (Utility)

Self-hosted FastAPI + Jinja2 form app for curator-driven track metadata JSON emission.

## Run locally

```bash
uvicorn niagads.genomicsdb_service.utilities.track_metadata_builder.app:app --reload
```

Then open <http://127.0.0.1:8000/>.

## Notes

- Input is form-based; no JSON editing required.
- Multi-value fields accept one value per line.
- Ontology term lists accept one item per line using `term|term_id`.
- Output is validated JSON download only (no database loading).
