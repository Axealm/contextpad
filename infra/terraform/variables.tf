variable "aws_region" {
  description = "AWS region for ContextPad."
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "Project name used in resource names."
  type        = string
  default     = "contextpad"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "runtime_mode" {
  description = "API runtime mode. Choose lambda or ecs."
  type        = string
  default     = "lambda"

  validation {
    condition     = contains(["lambda", "ecs"], var.runtime_mode)
    error_message = "runtime_mode must be lambda or ecs."
  }
}
