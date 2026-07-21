output "budget_name" {
  value       = aws_budgets_budget.free_tier.name
  description = "The name of the AWS budget created"
}
