# Sample 004: Module with reference arguments
# Test case where module arguments are references to other resources

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

# IAM Role in root module
resource "aws_iam_role" "app_role" {
  name        = "sample004-app-role"
  description = "Application role for S3 access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "sample004-app-role"
  }
}

# S3 Bucket in root module
resource "aws_s3_bucket" "data_bucket" {
  bucket = "sample004-data-bucket-unique-12345"

  tags = {
    Name = "sample004-data-bucket"
  }
}

# Module that takes references as arguments
module "storage" {
  source = "./modules/storage"

  # Pass resource references as module arguments
  bucket_name = aws_s3_bucket.data_bucket.bucket
  role_arn    = aws_iam_role.app_role.arn
  environment = "development"
}
