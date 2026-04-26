# reDocencIA V2 - Setup e Deploy

## Visao geral

Projeto full stack com:

- Frontend em React + Vite
- Backend em FastAPI
- Deploy na Vercel

Estrutura principal:

- `frontend/`: aplicacao web
- `backend/`: API e servicos
- `api/`: entrypoint para deploy serverless raiz

## Requisitos

- Python 3.11+
- Node.js 20+
- npm
- Vercel CLI (`vercel`)

## Setup local

### 1) Clonar o repositorio

```bash
git clone https://github.com/paulocavallari/reDocencIA-V2.git
cd reDocencIA-V2
```

### 2) Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

Variaveis minimas de ambiente do backend:

- `DATABASE_URL`
- `REDOCENCIA_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `OPENROUTER_API_KEY`

Opcional para cadastro admin no Supabase:

- `SUPABASE_SERVICE_ROLE_KEY`

Executar localmente:

```bash
uvicorn app.main:app --reload --port 8000
```

### 3) Frontend

```bash
cd ../frontend
npm install
```

Variaveis minimas de ambiente do frontend:

- `VITE_API_BASE_URL` (ex.: `http://127.0.0.1:8000`)
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Executar localmente:

```bash
npm run dev
```

## Deploy

### Frontend (Vercel)

```bash
cd frontend
vercel deploy --prod
```

### Backend (Vercel)

```bash
cd backend
vercel deploy --prod
```

## Fluxo recomendado de branch

- Branch principal: `main`
- Feature branches a partir de `main`
- Merge via Pull Request

## Troubleshooting rapido

- Se a API retornar erro de invocacao na Vercel:
  - validar envs no projeto `backend`
  - validar entrypoint `backend/api/index.py`
  - validar roteamento em `backend/vercel.json`
- Se o frontend nao chamar a API correta:
  - validar `VITE_API_BASE_URL`
  - garantir que o cliente faz trim da URL antes de usar
