output "environment" {
  value = module.resources.environment
}

output "resources" {
  value = module.resources
  sensitive = true
}

