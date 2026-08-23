# Service Studio Development Rules

This repository owns Service Studio PawApp features 12-15. Product behavior belongs here, not in generated copies under `zhiyun-ai-platform/apps/qwenpaw-embedded/workspace/plugins`.

- QwenPaw 2.1.0 is the supported runtime. Preserve `plugin.json` manifest and the Data Core integration contract.
- Read `docs/PRD.md` and `docs/PROGRESS.md` before changing product behavior.
- Never commit directly to `main`, force-push a shared branch, or merge automatically.
- Do not claim a capability is available without a real-data UI/backend/Agent path and reproducible acceptance evidence. Simulated data must remain optional and clearly labeled.
- Run `python scripts/verify_release.py` before delivery.
- Preserve user data and rollback paths. Never commit secrets, customer data, runtime caches, or generated installations.
