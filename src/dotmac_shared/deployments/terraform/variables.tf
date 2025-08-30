# Variables for DotMac Framework Infrastructure

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "dotmac-framework"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "dotmac-production"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.large"
}

variable "db_storage_size" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_max_storage_size" {
  description = "RDS maximum storage size in GB"
  type        = number
  default     = 1000
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "dotmac"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r7g.large"
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the cluster"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

# Monitoring Configuration
variable "enable_cloudwatch_logs" {
  description = "Enable CloudWatch logs"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention days"
  type        = number
  default     = 30
}

# Scaling Configuration
variable "min_cluster_size" {
  description = "Minimum number of nodes in the cluster"
  type        = number
  default     = 3
}

variable "max_cluster_size" {
  description = "Maximum number of nodes in the cluster"
  type        = number
  default     = 20
}

variable "desired_cluster_size" {
  description = "Desired number of nodes in the cluster"
  type        = number
  default     = 6
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "spot_instance_types" {
  description = "Instance types for spot instances"
  type        = list(string)
  default     = ["m5.large", "m5.xlarge", "m5a.large", "m5a.xlarge"]
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "dotmac-framework"
    Terraform   = "true"
    Owner       = "dotmac-team"
  }
}
