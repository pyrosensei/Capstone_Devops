variable "namespace" { type = string }
variable "image_tag" { type = string }
variable "secret_key" {
  type      = string
  sensitive = true
}
variable "postgres_password" {
  type      = string
  sensitive = true
}
variable "database_url" {
  type      = string
  sensitive = true
}
variable "bootstrap_admin_password" {
  type      = string
  sensitive = true
}
variable "bootstrap_dev_password" {
  type      = string
  sensitive = true
}
variable "metrics_token" {
  type      = string
  sensitive = true
}
variable "repo_root" {
  type    = string
  default = ".."
}
variable "k8s_overlay" {
  type    = string
  default = "kubernetes/overlays/dev"
}
variable "apply_manifests" {
  type        = bool
  default     = false
  description = "Run kubectl apply -k for the generated configuration."
}
