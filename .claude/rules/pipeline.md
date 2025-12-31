CICD (GitHub Actions, GitLab, CodePipeline)

5.1 Segurança
• Scanners automáticos:
• Snyk / Trivy → dependências
• Semgrep → secure coding
• Checkov → Terraform / infra-as-code
• Assinatura de commits (GPG)

5.2 Pipeline
• Build → Test → Lint → Security Scan → Deploy
• Deploy Blue/Green ou Canary
• Aprovação manual para produção
