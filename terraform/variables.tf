variable "region" {
  default = "ap-southeast-1"
}

variable "cluster_name" {
  default = "lta-proxy"
}

variable "admin_iam_arn" {
  description = "Your IAM user/role ARN. Get it with: aws sts get-caller-identity --query Arn --output text"
  type        = string
}
