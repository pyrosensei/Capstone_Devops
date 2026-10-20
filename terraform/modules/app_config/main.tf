resource "local_file" "runtime_config" {
  filename = "${path.module}/generated/app.env"
  content  = <<-EOT
    APP_ENV=kubernetes
    K8S_NAMESPACE=${var.namespace}
    IMAGE_TAG=${var.image_tag}
    SECRET_KEY=${var.secret_key}
  EOT
}

resource "null_resource" "apply_manifests" {
  count = var.apply_manifests ? 1 : 0

  triggers = {
    overlay = var.k8s_overlay
    env     = local_file.runtime_config.content
  }

  provisioner "local-exec" {
    command = "kubectl apply -k ${var.repo_root}/${var.k8s_overlay}"
  }
}

output "namespace" {
  value = var.namespace
}

output "config_path" {
  value = local_file.runtime_config.filename
}
