variable "cluster_name" {
  type        = string
  default     = "devplane-kind"
  description = "Local kind cluster name"
}

variable "enable_kind" {
  type        = bool
  default     = false
  description = "When true, terraform apply will invoke kind. Requires kind on PATH."
}

variable "is_windows" {
  type        = bool
  default     = false
  description = "Set true on Windows so local-exec uses PowerShell syntax."
}

variable "repo_root" {
  type        = string
  default     = ".."
  description = "Repository root relative to terraform/."
}

variable "install_ingress" {
  type        = bool
  default     = false
  description = "Install ingress-nginx into the local kind cluster."
}

variable "apply_manifests" {
  type        = bool
  default     = false
  description = "Apply kubernetes/overlays/dev with kubectl after provisioning."
}

variable "namespace" {
  type    = string
  default = "devplane"
}

variable "image_tag" {
  type    = string
  default = "local"
}

variable "secret_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional JWT signing key. Leave empty to generate one with Terraform."
}

variable "bootstrap_admin_password" {
  type        = string
  default     = "admin123"
  sensitive   = true
  description = "Demo bootstrap admin password. The dev overlay sets DEMO_MODE=true."
}

variable "bootstrap_dev_password" {
  type        = string
  default     = "dev123"
  sensitive   = true
  description = "Demo bootstrap developer password. The dev overlay sets DEMO_MODE=true."
}
