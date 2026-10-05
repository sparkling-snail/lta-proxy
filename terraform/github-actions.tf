# --------------------------------------------------------------------------
# GitHub Actions OIDC
#
# Lets the CI/CD workflow (.github/workflows/deploy.yml) assume an AWS role
# via a short-lived token — no long-lived AWS access keys stored as GitHub
# secrets. The resulting role ARN goes into the AWS_DEPLOY_ROLE_ARN secret.
# --------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  # GitHub's OIDC thumbprint is no longer checked by AWS (it validates via
  # the TLS cert chain instead), but the argument is still required.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea"]
}

resource "aws_iam_role" "github_actions" {
  name = "${var.cluster_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        # Only workflows running on this exact repo can assume the role —
        # any branch, since deploy.yml triggers on both main and test_local.
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

# Push/pull images in both ECR repos
resource "aws_iam_role_policy_attachment" "github_actions_ecr" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
  role       = aws_iam_role.github_actions.name
}

# Needed for `aws eks update-kubeconfig` to resolve the cluster endpoint/CA
resource "aws_iam_role_policy" "github_actions_eks_describe" {
  name = "eks-describe"
  role = aws_iam_role.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "eks:DescribeCluster"
      Resource = aws_eks_cluster.main.arn
    }]
  })
}

# Grant the role kubectl access, but only to the lta-proxy namespace —
# deploy.yml only needs to set image + check rollout status there.
resource "aws_eks_access_entry" "github_actions" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_iam_role.github_actions.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "github_actions" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_iam_role.github_actions.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  access_scope {
    type       = "namespace"
    namespaces = ["lta-proxy"]
  }
}
