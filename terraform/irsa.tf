# --------------------------------------------------------------------------
# IRSA — IAM Roles for Service Accounts
#
# EKS OIDC provider lets Kubernetes pods assume IAM roles directly.
# Without this, the AWS Load Balancer Controller can't call the AWS API
# to create ALBs when you apply k8s/ingress.yaml.
# --------------------------------------------------------------------------

# Pull the OIDC issuer certificate from the EKS cluster
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# Register EKS as a trusted OIDC identity provider in IAM
resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# --------------------------------------------------------------------------
# AWS Load Balancer Controller IAM role
#
# The controller runs as a pod in kube-system. Via IRSA, it assumes this
# role to call EC2/ELB APIs and create the ALB when you apply ingress.yaml.
# --------------------------------------------------------------------------

# Fetch the official LBC IAM policy from the upstream repo
data "http" "lbc_policy" {
  url = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/docs/install/iam_policy.json"
}

resource "aws_iam_policy" "lbc" {
  name   = "${var.cluster_name}-lbc-policy"
  policy = data.http.lbc_policy.response_body
}

resource "aws_iam_role" "lbc" {
  name = "${var.cluster_name}-lbc-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lbc" {
  policy_arn = aws_iam_policy.lbc.arn
  role       = aws_iam_role.lbc.name
}
