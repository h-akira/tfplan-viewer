# Test007: Modules with cross-module references
# - VPC module (creates VPC and Subnet)
# - App module (creates Security Group, Lambda Role, Lambda Function)
# - Root module coordinates both

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  vpc_cidr = "10.0.0.0/16"
  vpc_name = "test007-vpc"
}

# App Module
module "app" {
  source = "./modules/app"

  vpc_id    = module.vpc.vpc_id
  subnet_id = module.vpc.subnet_id
  app_name  = "test007-app"
}

# S3 Bucket in root module
resource "aws_s3_bucket" "shared" {
  bucket = "test007-shared-bucket-unique-98765"

  tags = {
    Name = "test007-shared-bucket"
  }
}
