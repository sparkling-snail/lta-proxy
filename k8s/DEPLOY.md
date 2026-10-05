# v3 EKS deploy runbook

One-time setup to go from `terraform apply` to a working cluster. After this,
pushes to `main`/`test_local` redeploy automatically via `.github/workflows/deploy.yml`.

## 1. Provision infra

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in admin_iam_arn
terraform init
terraform apply
```

Grab these from the output — you'll need them below:

```bash
terraform output kubeconfig_command
terraform output app_ecr_url
terraform output frontend_ecr_url
terraform output github_actions_role_arn
terraform output lbc_role_arn
```

## 2. Point kubectl at the cluster

```bash
$(terraform output -raw kubeconfig_command)
kubectl get nodes   # sanity check
```

## 3. Install the AWS Load Balancer Controller

Required before `k8s/ingress.yaml` can provision an ALB — the controller is
what watches Ingress objects and talks to the EC2/ELB API.

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=lta-proxy \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="$(terraform -chdir=terraform output -raw lbc_role_arn)"
```

## 4. Install kube-prometheus-stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prom prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --values helm/kube-prometheus-values.yaml
```

## 5. Create the app secret

```bash
cp k8s/app/secret.yaml.example k8s/app/secret.yaml
# edit k8s/app/secret.yaml and fill in LTA_API_KEY (this file is gitignored)
```

## 6. First-time image push

The manifests reference ECR image placeholders that don't exist yet, and CI/CD
hasn't run once to populate them. Build and push manually, once:

```bash
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin "$(terraform -chdir=terraform output -raw app_ecr_url | cut -d/ -f1)"

docker build -t "$(terraform -chdir=terraform output -raw app_ecr_url):init" .
docker push "$(terraform -chdir=terraform output -raw app_ecr_url):init"

docker build -t "$(terraform -chdir=terraform output -raw frontend_ecr_url):init" ./frontend
docker push "$(terraform -chdir=terraform output -raw frontend_ecr_url):init"
```

Then edit the `image:` field in `k8s/app/deployment.yaml` and
`k8s/frontend/deployment.yaml` to point at `<ecr_url>:init` (replacing the
`REPLACE_WITH_ECR_*_URL:latest` placeholders).

## 7. Apply the manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/app/configmap.yaml -f k8s/app/secret.yaml -f k8s/app/deployment.yaml -f k8s/app/service.yaml -f k8s/app/hpa.yaml
kubectl apply -f k8s/frontend/deployment.yaml -f k8s/frontend/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/monitoring/service-monitor.yaml -f k8s/monitoring/prometheus-rule.yaml

kubectl get ingress -n lta-proxy   # wait for an ADDRESS to appear — that's the ALB DNS name
```

## 8. Wire up CI/CD

In the GitHub repo settings → Secrets and variables → Actions, add:

- `AWS_DEPLOY_ROLE_ARN` = `terraform output -raw github_actions_role_arn`

From here on, `git push` to `main` or `test_local` builds, pushes, and rolls
out both deployments automatically.

## Teardown

```bash
helm uninstall kube-prom -n monitoring
helm uninstall aws-load-balancer-controller -n kube-system
kubectl delete -f k8s/ --recursive
cd terraform && terraform destroy
```

Destroy the Helm releases first — the ALB and EBS volumes they created aren't
Terraform-managed and will orphan AWS resources (and cost) if skipped.
