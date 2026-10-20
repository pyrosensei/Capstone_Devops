# Git branch strategy

- `main` — always demo-ready. Protected in a real GitHub org.
- `feature/<topic>` — one syllabus phase or product slice (catalog, k8s, monitoring).
- `fix/<issue>` — bugfixes.

Suggested flow:

1. Branch from `main`.
2. Small, meaningful commits (see README commit history notes).
3. Open a pull request; Jenkins builds `Jenkinsfile`.
4. Merge squash or merge commit into `main`.
5. Argo CD syncs `kubernetes/overlays/dev`.

Commit message style: `phaseN: imperative summary` e.g. `phase3: add multi-stage non-root Dockerfile`.
