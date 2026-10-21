# Git branch strategy

- `main` - always demo-ready. Protect it in a real GitHub organization.
- `feature/<topic>` - one syllabus phase or product slice, such as `feature/kubernetes` or `feature/observability`.
- `fix/<issue>` - bug fixes.
- `docs/<topic>` - documentation-only changes.

Suggested flow:

1. Branch from `main`.
2. Keep commits small and meaningful.
3. Open a pull request; Jenkins builds the `Jenkinsfile` for the branch.
4. Review tests, lint, and the Docker build.
5. Squash-merge or merge into `main`.
6. Argo CD syncs `kubernetes/overlays/dev` if it is installed against the repository.

Commit message style:

```text
phase3: add multi-stage non-root Dockerfile
fix: wait for ingress admission before applying manifests
docs: rewrite Kubernetes runbook
```

Do not commit `.env`, kubeconfigs, tokens, registry credentials, or generated coverage artifacts.
