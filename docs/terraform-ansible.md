# Ansible and Terraform

Both tools automate the path from a fresh host to a running DevPlane stack. They are separate options: Ansible targets Linux hosts, while Terraform provisions the local kind cluster and can apply the manifests.

## Ansible

Requirements:

- Linux host or WSL2 on Windows.
- Ansible installed on the control node.
- `sudo`/`become` access for the Docker role.

Inventory in `ansible/inventory.ini` uses a local connection:

```ini
[local]
localhost ansible_connection=local
```

Playbooks:

```bash
cd ansible
ansible-playbook playbooks/install-tools.yml
ansible-playbook playbooks/site.yml
ansible-playbook playbooks/k8s-deploy.yml
```

### `install-tools.yml`

Installs:

- Docker Engine, CLI, containerd, Buildx, and the Compose plugin on Debian/Ubuntu.
- kubectl, kind, and Helm binaries into `/usr/local/bin`.

The Docker role adds the invoking user to the `docker` group. Log out and back in (or use `newgrp docker`) before running Docker without sudo.

### `site.yml`

Builds and starts the Compose stack and waits for `http://127.0.0.1:8000/health/ready`.

Because it uses the local inventory, it installs packages on the machine where Ansible runs. Use a Linux VM or WSL2; the Debian/Ubuntu assertion will fail elsewhere.

### `k8s-deploy.yml`

Creates the kind cluster if needed, builds and loads the image, installs ingress-nginx, applies `kubernetes/overlays/dev`, and waits for both deployments.

If ingress admission is still starting on a slow machine, wait and re-run:

```bash
kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=180s
kubectl apply -k kubernetes/overlays/dev
```

### Tags

```bash
ansible-playbook playbooks/site.yml --tags docker
ansible-playbook playbooks/site.yml --tags k8s-tools
ansible-playbook playbooks/site.yml --tags deploy
```

## Terraform

Requirements:

- Terraform >= 1.5
- Docker, kind, and kubectl for a local kind run
- PowerShell on Windows because the modules switch syntax with `is_windows`

Files:

- `terraform/main.tf` - root module wiring.
- `terraform/modules/kind_cluster` - generates kind config, creates the cluster, builds/loads the image, optionally installs ingress.
- `terraform/modules/app_config` - renders runtime config and optionally applies the Kustomize overlay.
- `terraform/cloud-stubs/` - example AWS/Azure/GCP files, not active modules.

### Run

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Windows:

```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Set these values for a local kind demo:

```hcl
cluster_name    = "devplane-kind"
enable_kind     = true
is_windows      = true
install_ingress = true
apply_manifests = true
namespace       = "devplane"
image_tag       = "local"
repo_root       = ".."
```

Set `is_windows = false` on Linux/macOS.

### What it creates

- `modules/kind_cluster/generated/kind-config.yaml`
- A kind cluster named by `cluster_name`
- A locally built `devplane-api:local` image loaded into kind
- Optional ingress-nginx installation
- `modules/app_config/generated/app.env` with namespace, image tag, and secret key
- Optional `kubectl apply -k kubernetes/overlays/dev`

### Outputs

```bash
terraform output
terraform output -raw kubeconfig_hint
```

### Destroy

```bash
terraform destroy
```

The kind cluster is created by a `null_resource` local-exec, so Terraform does not own the cluster's full lifecycle. Delete it explicitly if needed:

```bash
kind delete cluster --name devplane-kind
```

## Validation status

Validated locally:

- Terraform 1.16.6: `fmt -check -recursive`, `validate`, and `plan` all pass. The plan creates only the generated kind config and application env file; `enable_kind` remains false by default.
- Ansible 2.19: `site.yml`, `k8s-deploy.yml`, and `install-tools.yml` pass `--syntax-check` from WSL.
- The playbooks were not applied to a fresh Linux host because the local machine is Windows and the roles install packages with `apt`. The manual equivalent (Docker build, kind create, kubectl apply, Compose, Helm) was executed successfully.

Ansible does not support a Windows control node; run it from WSL2 or a Linux VM. On this machine, use:

```bash
cd ansible
ANSIBLE_CONFIG=$PWD/ansible.cfg \
ANSIBLE_ROLES_PATH=$PWD/roles \
ansible-playbook --syntax-check playbooks/site.yml
```
