# Improvements (backend, UI, business logic)

This document tracks practical fixes to make the system easier to demo end-to-end and more robust for real usage.

## Business logic (Phase 1–2)
- **Location canonicalization everywhere**: normalize user input and dataset locations consistently (e.g., `Bengaluru`, `South Bangalore` → `Bangalore`) so users don’t get “0 results” due to spelling/region variants.
- **Parquet refresh behavior**: Phase 1 ingestion should refresh `restaurants.parquet` so schema/normalization changes don’t leave stale records.
- **Safer parquet list parsing**: handle cuisines/tags stored as lists, numpy arrays, or nulls without pandas truthiness errors.
- **Clear relaxation messaging**: Phase 2 should return `relaxations_applied` and show it in UI.

## Backend (Phase 4 FastAPI)
- **Input normalization**: canonicalize `location` server-side (so UI/clients don’t need to know synonyms).
- **Better errors**: return actionable error messages for missing parquet / empty store and invalid request fields.
- **CORS (optional)**: allow local web UI if hosted separately later.

## Frontend (Phase 4 basic UI)
- **Better UX on “no results”**: show relaxations + suggestions (e.g., try `Bangalore`/`Delhi`).
- **Validation**: prevent empty cuisines and non-positive budget in UI before calling API.

## Docs
- **Architecture clarity**: document that Phase 4 UI is basic and Phase 4 backend normalizes inputs.

