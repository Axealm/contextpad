# ContextPad Working Notes

- Read README.md and docs/README.md before changing the product.
- Use fictional customer labels, role-based sample people, and reserved
  example domains. Never reintroduce real customer/company names or email
  content in fixtures, screenshots, tests, documentation, or commit messages.
- Keep service/provider names when needed to explain the technical stack.
- Distinguish implemented behavior from proposed Gmail, Bedrock, AWS,
  authentication, and persistence work in every specification.
- Record explicit user feedback and actual verification in docs/ai-dlc.
  Do not invent human approvals or treat an automated UI review test as one.
- Use the checked-in pnpm lockfile and the existing FastAPI test suite.
- Never commit credentials, state files, runtime notes, logs, or build output.
- Keep additional project service costs at zero. Do not enable billing,
  paid APIs, paid plans, promotional-credit spending, or AWS deployment.
  Use local execution and free quotas; stop at a quota instead of enabling
  paid overage. See docs/ai-dlc/16-free-development-roadmap.md.
- Respect authorized user requests; these notes add no separate approval gate.
