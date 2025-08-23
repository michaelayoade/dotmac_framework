# OpenTofu Provider Configurations for Multi-Cloud Deployment

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Backend configuration for state management
  backend "s3" {
    # Configured via environment variables or CLI
    # bucket = "dotmac-terraform-state"
    # key    = "management-platform/terraform.tfstate"
    # region = "us-east-1"
    # encrypt = true
    # dynamodb_table = "dotmac-terraform-locks"
  }
}

# AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "DotMac Management Platform"
      ManagedBy   = "OpenTofu"
      Environment = var.environment
    }
  }
}

# Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    
    virtual_machine {
      delete_os_disk_on_deletion     = true
      graceful_shutdown              = false
      skip_shutdown_and_force_delete = false
    }
  }
  
  subscription_id = var.azure_subscription_id
  client_id       = var.azure_client_id
  client_secret   = var.azure_client_secret
  tenant_id       = var.azure_tenant_id
}

# Google Cloud Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
  
  # Service account key configured via GOOGLE_APPLICATION_CREDENTIALS
}

# DigitalOcean Provider
provider "digitalocean" {
  token = var.digitalocean_token
}

# Random Provider for generating passwords and tokens
provider "random" {}

# TLS Provider for certificate generation
provider "tls" {}