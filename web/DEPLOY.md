# Deploy no Veloz

## 1. Supabase — Executar SQL Migration

No painel do Supabase → SQL Editor, execute o conteúdo de:
`supabase/migrations/001_schema.sql`

Isso cria as tabelas `scrim_sessions`, `session_players`, `champion_pool_cache` e as políticas RLS.

## 2. Configurar .env.local

Já preenchido com URL e anon key.
Você ainda precisa adicionar:
- `SUPABASE_SERVICE_ROLE_KEY` — em Supabase → Settings → API → service_role key
- `API_TOKEN` — qualquer string segura (ex: `openssl rand -hex 32`), usada para autenticar o VisionLOL

## 3. Deploy no Veloz

```bash
cd web
npm i -g onveloz   # se ainda não instalado
veloz login
veloz deploy
```

Depois do deploy, copie a URL gerada (ex: `https://visionlol.veloz.app`).

## 4. Configurar VisionLOL Desktop

No botão `🌐 Publicar` de qualquer sessão de scrim:
- URL: URL do Veloz acima
- Token: mesmo valor de `API_TOKEN` no `.env.local`

Clique em "Testar Conexão" para validar, depois "Salvar e Publicar".
