variable "cluster_name" {
  type        = string
  description = "Local kind cluster name"
}

variable "enable_kind" {
  type        = bool
  description = "When true, create the local kind cluster with local-exec."
}

variable "is_windows" {
  type        = bool
  description = "Use PowerShell syntax for local-exec commands."
  default     = false
}

variable "image_name" {
  type        = string
  description = "Application image to build and load into kind."
  default     = "devplane-api:local"
}

variable "repo_root" {
  type        = string
  description = "Repository root on the machine running Terraform."
  default     = ".."
}

variable "install_ingress" {
  type        = bool
  description = "Install ingress-nginx into the kind cluster."
  default     = false
}
