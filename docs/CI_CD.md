# CI/CD moderno (GitHub Actions + deploy automatico)

Este projeto agora possui duas pipelines:

- `CI` (`.github/workflows/ci.yml`): lint, testes, auditoria de dependencias e build de imagem Docker.
- `CD` (`.github/workflows/cd.yml`): deploy automatico em producao quando o CI do `main` passar.

## 1) O que voce ganha

- Validacao de qualidade em pull requests.
- Publicacao automatica de imagem no GHCR em push para `main`.
- Deploy automatizado por webhook (Render, Railway, Fly.io, Coolify, etc.).
- Smoke test de saude apos deploy para feedback visual no Actions.

## 2) Secrets necessarios

No repositorio (GitHub -> Settings -> Secrets and variables -> Actions), configure:

- `APP_DEPLOY_WEBHOOK_URL` (obrigatorio): endpoint HTTP POST para disparar deploy no provedor.
- `APP_PUBLIC_URL` (opcional, recomendado): URL publica da app para health check (ex.: `https://meu-app.onrender.com`).

## 3) Ambiente protegido (recomendado)

Crie o environment `production` em `Settings -> Environments` e:

- adicione reviewers obrigatorios para aprovar deploy;
- mova os secrets de producao para esse environment.

## 4) Fluxo de deploy automatico

1. Merge de PR no branch `main`.
2. Workflow `CI` executa: lint + testes + seguranca + build/push de imagem.
3. Se sucesso, workflow `CD` dispara automaticamente.
4. `CD` chama `APP_DEPLOY_WEBHOOK_URL`.
5. Se `APP_PUBLIC_URL` existir, o `CD` valida `/_stcore/health`.

## 5) Como visualizar o deploy

- Aba **Actions** do GitHub:
  - veja o status do `CI` e do `CD`;
  - abra cada job para logs detalhados;
  - acompanhe retries e health check no job `Deploy to production`.
- Aba **Packages**:
  - acompanhe as imagens versionadas no GHCR (`ghcr.io/<owner>/<repo>`).

## 6) Sugestao de provedores

- **Render**: use Deploy Hook no servico web.
- **Railway**: use webhook de deploy/redeploy do projeto.
- **Fly.io**: use webhook proprio (ou troque o passo de webhook por `flyctl deploy` com token).

## 7) Proximos upgrades recomendados

- Adicionar cobertura de testes + badge.
- Incluir SAST (CodeQL) e dependabot.
- Adicionar estrategia blue/green ou canary no provedor.
