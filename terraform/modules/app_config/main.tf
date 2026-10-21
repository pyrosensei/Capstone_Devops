resource "local_file" "runtime_config" {
  filename = "${path.module}/generated/app.env"
  content  = <<-EOT
    APP_ENV=kubernetes
    K8S_NAMESPACE=${var.namespace}
    IMAGE_TAG=${var.image_tag}
  EOT
}

resource "null_resource" "apply_manifests" {
  count = var.apply_manifests ? 1 : 0

  triggers = {
    overlay           = var.k8s_overlay
    namespace         = var.namespace
    secret_key        = var.secret_key
    postgres_password = var.postgres_password
    database_url      = var.database_url
  }

  provisioner "local-exec" {
    command = "kubectl create namespace ${var.namespace} --dry-run=client -o yaml | kubectl apply -f - && kubectl -n ${var.namespace} create secret generic devplane-secrets --from-literal=SECRET_KEY=\"${var.secret_key}\" --from-literal=POSTGRES_PASSWORD=\"${var.postgres_password}\" --from-literal=DATABASE_URL=\"${var.database_url}\" --from-literal=BOOTSTRAP_ADMIN_PASSWORD=\"${var.bootstrap_admin_password}\" --from-literal=BOOTSTRAP_DEV_PASSWORD=\"${var.bootstrap_dev_password}\" --dry-run=client -o yaml | kubectl apply -f - && kubectl apply -k ${var.repo_root}/${var.k8s_overlay} && kubectl -n ${var.namespace} rollout restart deploy/devplane-api deploy/devplane-worker"
  }
}

output "namespace" {
  value = var.namespace
}

output "config_path" {
  value = local_file.runtime_config.filename
}
