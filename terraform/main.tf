terraform {
  required_version = ">= 1.5.0"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

module "kind_cluster" {
  source          = "./modules/kind_cluster"
  cluster_name    = var.cluster_name
  enable_kind     = var.enable_kind
  is_windows      = var.is_windows
  repo_root       = var.repo_root
  install_ingress = var.install_ingress
}

module "app_config" {
  source          = "./modules/app_config"
  namespace       = var.namespace
  image_tag       = var.image_tag
  secret_key      = var.secret_key
  repo_root       = var.repo_root
  apply_manifests = var.apply_manifests

  depends_on = [module.kind_cluster]
}

output "cluster_name" {
  value = module.kind_cluster.cluster_name
}

output "kubeconfig_hint" {
  value = module.kind_cluster.kubeconfig_hint
}

output "kind_config_path" {
  value = module.kind_cluster.kind_config_path
}

output "namespace" {
  value = module.app_config.namespace
}

output "rendered_config_path" {
  value = module.app_config.config_path
}
