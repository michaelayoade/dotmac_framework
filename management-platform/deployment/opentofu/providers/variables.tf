# Global Variables for Multi-Cloud Providers

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "dotmac-mgmt"
}

variable "tenant_id" {
  description = "Tenant ID for multi-tenant deployments"
  type        = string
}

variable "region" {
  description = "Primary deployment region"
  type        = string
  default     = "us-east-1"
}

# ============================================================================
# AWS Variables
# ============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_availability_zones" {
  description = "AWS availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "aws_instance_types" {
  description = "EC2 instance types for different components"
  type = object({
    web         = string
    api         = string
    database    = string
    worker      = string
    monitoring  = string
  })
  default = {
    web         = "t3.medium"
    api         = "t3.large"
    database    = "t3.large"
    worker      = "t3.medium"
    monitoring  = "t3.xlarge"
  }
}

# ============================================================================
# Azure Variables
# ============================================================================

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "azure_client_id" {
  description = "Azure client ID"
  type        = string
  sensitive   = true
}

variable "azure_client_secret" {
  description = "Azure client secret"
  type        = string
  sensitive   = true
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "azure_location" {
  description = "Azure location for deployment"
  type        = string
  default     = "East US"
}

variable "azure_vm_sizes" {
  description = "Azure VM sizes for different components"
  type = object({
    web         = string
    api         = string
    database    = string
    worker      = string
    monitoring  = string
  })
  default = {
    web         = "Standard_B2s"
    api         = "Standard_B4ms"
    database    = "Standard_B4ms"
    worker      = "Standard_B2s"
    monitoring  = "Standard_B8ms"
  }
}

# ============================================================================
# Google Cloud Variables
# ============================================================================

variable "gcp_project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "Google Cloud zone"
  type        = string
  default     = "us-central1-a"
}

variable "gcp_machine_types" {
  description = "GCP machine types for different components"
  type = object({
    web         = string
    api         = string
    database    = string
    worker      = string
    monitoring  = string
  })
  default = {
    web         = "e2-medium"
    api         = "e2-standard-4"
    database    = "e2-standard-4"
    worker      = "e2-medium"
    monitoring  = "e2-standard-8"
  }
}

# ============================================================================
# DigitalOcean Variables
# ============================================================================

variable "digitalocean_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "digitalocean_region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc1"
}

variable "digitalocean_sizes" {
  description = "DigitalOcean droplet sizes"
  type = object({
    web         = string
    api         = string
    database    = string
    worker      = string
    monitoring  = string
  })
  default = {
    web         = "s-2vcpu-2gb"
    api         = "s-4vcpu-8gb"
    database    = "s-4vcpu-8gb"
    worker      = "s-2vcpu-4gb"
    monitoring  = "s-8vcpu-16gb"
  }
}

# ============================================================================
# Networking Variables
# ============================================================================

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# ============================================================================
# Database Variables
# ============================================================================

variable "database_config" {
  description = "Database configuration"
  type = object({
    engine_version    = string
    instance_class    = string
    allocated_storage = number
    multi_az         = bool
    backup_retention = number
  })
  default = {
    engine_version    = "15.4"
    instance_class    = "db.t3.large"
    allocated_storage = 100
    multi_az         = true
    backup_retention = 7
  }
}

# ============================================================================
# Security Variables
# ============================================================================

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict in production
}

variable "allowed_http_cidrs" {
  description = "CIDR blocks allowed for HTTP/HTTPS access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssl_certificate_arn" {
  description = "SSL certificate ARN for load balancers"
  type        = string
  default     = ""
}

# ============================================================================
# Monitoring Variables
# ============================================================================

variable "monitoring_config" {
  description = "Monitoring configuration"
  type = object({
    enable_detailed_monitoring = bool
    log_retention_days        = number
    alert_email              = string
  })
  default = {
    enable_detailed_monitoring = true
    log_retention_days        = 30
    alert_email              = "alerts@dotmac.io"
  }
}

# ============================================================================
# Backup Variables
# ============================================================================

variable "backup_config" {
  description = "Backup configuration"
  type = object({
    retention_days = number
    backup_window  = string
    schedule       = string
  })
  default = {
    retention_days = 30
    backup_window  = "03:00-05:00"
    schedule       = "cron(0 2 * * ? *)"
  }
}

# ============================================================================
# Scaling Variables
# ============================================================================

variable "scaling_config" {
  description = "Auto-scaling configuration"
  type = object({
    min_size                = number
    max_size                = number
    desired_capacity        = number
    scale_up_threshold      = number
    scale_down_threshold    = number
  })
  default = {
    min_size                = 1
    max_size                = 10
    desired_capacity        = 2
    scale_up_threshold      = 75
    scale_down_threshold    = 25
  }
}

# ============================================================================
# Common Tags
# ============================================================================

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "DotMac Management Platform"
    ManagedBy   = "OpenTofu"
    Owner       = "DevOps Team"
    CostCenter  = "Engineering"
  }
}