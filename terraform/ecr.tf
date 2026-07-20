resource "aws_ecr_repository" "app" {
  name                 = "lta-proxy"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # terraform destroy cleans up images too
}

resource "aws_ecr_repository" "frontend" {
  name                 = "lta-proxy-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# Keep only the last 5 images in each repo — ECR storage isn't free
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
