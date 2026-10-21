resource "local_file" "kind_config" {
  filename = "${path.module}/generated/kind-config.yaml"
  content  = <<-YAML
    kind: Cluster
    apiVersion: kind.x-k8s.io/v1alpha4
    nodes:
      - role: control-plane
        kubeadmConfigPatches:
          - |
            kind: InitConfiguration
            nodeRegistration:
              kubeletExtraArgs:
                node-labels: "ingress-ready=true"
        extraPortMappings:
          - containerPort: 80
            hostPort: 8081
            protocol: TCP
          - containerPort: 443
            hostPort: 8443
            protocol: TCP
  YAML
}

resource "null_resource" "kind_cluster" {
  count = var.enable_kind ? 1 : 0

  triggers = {
    cluster = var.cluster_name
    config  = local_file.kind_config.content
  }

  provisioner "local-exec" {
    command = var.is_windows ? (
      "powershell -NoProfile -Command \"if (-not ((kind get clusters) -contains '${var.cluster_name}')) { kind create cluster --name ${var.cluster_name} --config '${local_file.kind_config.filename}' }\""
      ) : (
      "kind get clusters | grep -qx '${var.cluster_name}' || kind create cluster --name ${var.cluster_name} --config ${local_file.kind_config.filename}"
    )
  }
}

resource "null_resource" "build_and_load_image" {
  count      = var.enable_kind ? 1 : 0
  depends_on = [null_resource.kind_cluster]

  triggers = {
    image  = var.image_name
    commit = fileexists("${var.repo_root}/.git/HEAD") ? file("${var.repo_root}/.git/HEAD") : "no-git"
  }

  provisioner "local-exec" {
    command = var.is_windows ? (
      "powershell -NoProfile -Command \"cd '${var.repo_root}'; docker build -t ${var.image_name} .; kind load docker-image ${var.image_name} --name ${var.cluster_name}\""
      ) : (
      "cd ${var.repo_root} && docker build -t ${var.image_name} . && kind load docker-image ${var.image_name} --name ${var.cluster_name}"
    )
  }
}

resource "null_resource" "ingress" {
  count      = var.enable_kind && var.install_ingress ? 1 : 0
  depends_on = [null_resource.kind_cluster]

  provisioner "local-exec" {
    command = "kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml && kubectl -n ingress-nginx wait --for=condition=Available deployment/ingress-nginx-controller --timeout=240s && kubectl -n ingress-nginx wait --for=condition=complete job/ingress-nginx-admission-create --timeout=120s && kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=180s"
  }
}

output "cluster_name" {
  value = var.cluster_name
}

output "kubeconfig_hint" {
  value = "kind get kubeconfig --name ${var.cluster_name}"
}

output "kind_config_path" {
  value = local_file.kind_config.filename
}
