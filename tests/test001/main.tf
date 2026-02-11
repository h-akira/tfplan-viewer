# Sample 000: Basic resources test
# - IAM Role with simple attributes
# - S3 Bucket with simple attributes

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

# IAM Role for Lambda execution
resource "aws_iam_role" "sample_role" {
  name        = "sample-lambda-role"
  description = "Sample IAM role for Lambda function"

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
    Name        = "sample-lambda-role"
    Environment = "development"
    Project     = "terraform2sheet"
  }
}

# S3 Bucket for data storage
resource "aws_s3_bucket" "sample_bucket" {
  bucket        = "terraform2sheet-sample-bucket-001"
  force_destroy = false

  tags = {
    Name        = "sample-bucket"
    Environment = "development"
    Project     = "terraform2sheet"
  }
}
