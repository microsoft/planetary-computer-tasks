# provider "helm" {
#   kubernetes {
#     host                   = azurerm_kubernetes_cluster.rxetl.kube_config.0.host
#     username               = azurerm_kubernetes_cluster.rxetl.kube_config.0.username
#     password               = azurerm_kubernetes_cluster.rxetl.kube_config.0.password
#     client_certificate     = base64decode(azurerm_kubernetes_cluster.rxetl.kube_config.0.client_certificate)
#     client_key             = base64decode(azurerm_kubernetes_cluster.rxetl.kube_config.0.client_key)
#     cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.rxetl.kube_config.0.cluster_ca_certificate)
#   }
# }

# # ARGO ######

# resource "helm_release" "argo" {
#   name             = "argo-workflow"
#   repository       = "https://argoproj.github.io/argo-helm"
#   version          = "4.0.6"
#   chart            = "argo/argo-workflows"
#   namespace        = "argo"
#   create_namespace = true

#   values = [
#     file("chart_values/argo.yaml")
#   ]
# }

# # NGINX ######

# resource "helm_release" "ingress-nginx" {
#   name             = "ingress-nginx"
#   repository       = "https://kubernetes.github.io/ingress-nginx"
#   version          = "4.0.6"
#   chart            = "ingress-nginx"
#   namespace        = "ingress-nginx"
#   create_namespace = true

#   set {
#     name  = "controller.service.externalTrafficPolicy"
#     value = "Local"
#   }

#   set {
#     name  = "controller.service.loadBalancerIP"
#     value = azurerm_public_ip.rxetl.ip_address
#   }

#   set {
#     name  = "controller.service.annotations.\"service.beta.kubernetes.io/azure-dns-label-name\""
#     value = azurerm_public_ip.rxetl.domain_name_label
#   }
# }

# # PCTASKS SERVER ######

# # resource "helm_release" "pctasks-server" {
# #   name             = "pctasks-server"
# #   chart            = "../../helm/pctasks-server/"
# #   version          = "0.1.0"
# #   namespace        = "pc"
# #   create_namespace = true

# #   values = [
# #     templatefile("chart_values/pctasks-server.yaml", {
# #       cidrs = join("\", \"", data.azurerm_network_service_tags.in_datacenter_service_tags.address_prefixes)
# #     })
# #   ]

# #   set {
# #     name  = "controller.service.externalTrafficPolicy"
# #     value = "Local"
# #   }

# #   set {
# #     name  = "controller.service.loadBalancerIP"
# #     value = azurerm_public_ip.rxetl.ip_address
# #   }

# #   set {
# #     name  = "controller.service.annotations.\"service.beta.kubernetes.io/azure-dns-label-name\""
# #     value = azurerm_public_ip.rxetl.domain_name_label
# #   }
# # }


