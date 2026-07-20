# --------------------------------------------------------------------------
# EKS cluster
# --------------------------------------------------------------------------

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.32"

  vpc_config {
    subnet_ids             = aws_subnet.public[*].id
    endpoint_public_access = true
  }

  # Use the newer API-based access model instead of the aws-auth ConfigMap.
  # This lets Terraform manage who can kubectl into the cluster without
  # needing the Kubernetes provider bootstrapping dance.
  access_config {
    authentication_mode = "API"
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

# --------------------------------------------------------------------------
# Grant your IAM user/role cluster-admin access.
# Run `aws sts get-caller-identity` to get your ARN, then pass it as
# var.admin_iam_arn in terraform.tfvars.
# --------------------------------------------------------------------------

resource "aws_eks_access_entry" "admin" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.admin_iam_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "admin" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.admin_iam_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
}

# --------------------------------------------------------------------------
# Managed node group
#
# t3.small  = 2 vCPU, 2GB RAM — cheapest that runs K8s system pods + app.
# SPOT      = ~60% cheaper than on-demand; AWS drains the node gracefully
#             before reclaiming it so rolling updates still work.
# desired=1 = single node, single public IP — that's your entry point.
#
# NOTE: if you add kube-prometheus-stack later, upgrade to t3.medium.
# Prometheus alone needs ~500MB heap; t3.small will OOMKill it.
# --------------------------------------------------------------------------

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = aws_subnet.public[*].id

  # Multiple types so the spot market can pick whichever is available
  instance_types = ["t3.small", "t3.medium"]
  capacity_type  = "SPOT"

  scaling_config {
    desired_size = 1
    min_size     = 1
    max_size     = 2
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_ecr,
    aws_iam_role_policy_attachment.node_cni,
  ]
}
