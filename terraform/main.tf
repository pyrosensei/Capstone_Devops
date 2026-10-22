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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
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

resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "random_password" "postgres_password" {
  length  = 32
  special = false
}

resource "random_password" "metrics_token" {
  length  = 32
  special = false
}

locals {
  secret_key        = var.secret_key != "" ? var.secret_key : random_password.secret_key.result
  postgres_password = random_password.postgres_password.result
  metrics_token     = random_password.metrics_token.result
  database_url      = "postgresql+psycopg2://devplane:${local.postgres_password}@devplane-postgres:5432/devplane"
}

module "app_config" {
  source                   = "./modules/app_config"
  namespace                = var.namespace
  image_tag                = var.image_tag
  secret_key               = local.secret_key
  postgres_password        = local.postgres_password
  database_url             = local.database_url
  bootstrap_admin_password = var.bootstrap_admin_password
  bootstrap_dev_password   = var.bootstrap_dev_password
  metrics_token            = local.metrics_token
  repo_root                = var.repo_root
  apply_manifests          = var.apply_manifests

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
