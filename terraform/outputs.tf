output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "app_ecr_url" {
  value = aws_ecr_repository.app.repository_url
}

output "frontend_ecr_url" {
  value = aws_ecr_repository.frontend.repository_url
}

# Run this after apply to configure kubectl
output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${var.cluster_name} --region ${var.region}"
}

# Paste this into the GitHub repo secret AWS_DEPLOY_ROLE_ARN
output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

# Paste this into the AWS Load Balancer Controller's ServiceAccount annotation
# (eks.amazonaws.com/role-arn) before installing the controller via Helm
output "lbc_role_arn" {
  value = aws_iam_role.lbc.arn
}
