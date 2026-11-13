# AuthAPI - Sistema Completo de Autenticação

Projeto educacional completo de autenticação fullstack com **FastAPI** (backend) e **Next.js** (frontend).

## Funcionalidades

- [x] Registro de usuários com validação de senha
- [x] Login com JWT (access + refresh tokens)
- [x] Rotação de refresh tokens
- [x] Logout (revogação de token)
- [x] Recuperação de senha
- [x] Perfil do usuário (ler/atualizar)
- [x] Alteração de senha
- [x] Listagem de usuários (admin)
- [x] Desativação de contas (soft delete)
- [x] Validação de força de senha
- [x] CORS configurado
- [x] Documentação Swagger automática

## Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.11+, FastAPI, SQLite, aiosqlite |
| Frontend | Next.js 14, React 18, TypeScript, Axios |
| Auth | JWT (python-jose), bcrypt, refresh tokens |

## Estrutura do Projeto

```
auth-app/
├── backend/
│   ├── main.py              # Aplicação FastAPI
│   ├── requirements.txt     # Dependências Python
│   └── app/
│       ├── models.py        # Models Pydantic + camada DB
│       ├── schemas.py       # Schemas de requisição/resposta
│       ├── utils.py         # Funções de segurança (JWT, hash)
│       └── routers/
│           ├── auth.py      # Endpoints de auth
│           └── users.py     # Endpoints de usuários
└── frontend/
    ├── package.json
    ├── src/
    │   ├── app/
    │   │   ├── login/page.tsx
    │   │   ├── register/page.tsx
    │   │   └── dashboard/page.tsx
    │   ├── components/
    │   │   └── AuthContext.tsx
    │   └── styles/
    └── next.config.js
```

## Setup Rápido

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
python main.py
```

O servidor inicia em `http://localhost:8000` com documentação em `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

A aplicação roda em `http://localhost:3001`.

## Endpoints da API

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/register` | Registra novo usuário |
| POST | `/api/auth/login` | Faz login |
| POST | `/api/auth/refresh` | Renova tokens |
| POST | `/api/auth/logout` | Revoga refresh token |
| POST | `/api/auth/forgot-password` | Solicita reset de senha |
| POST | `/api/auth/reset-password` | Reseta senha com token |

### Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/users/me` | Dados do usuário logado |
| PATCH | `/api/users/me` | Atualiza perfil |
| PUT | `/api/users/me/password` | Altera senha |
| GET | `/api/users/` | Lista todos (admin) |
| DELETE | `/api/users/{id}` | Desativa conta |

## Segurança Implementada

1. **Hash de senhas**: bcrypt com salt automático
2. **JWT com expiry**: Access tokens expiram em 30 min, refresh em 7 dias
3. **Token rotation**: Refresh tokens são revogados ao usar
4. **Password strength**: Validação de força da senha no registro e mudança
5. **Soft delete**: Contas são desativadas, não deletadas
6. **CORS controlado**: Apenas origens permitidas
7. **Rate limiting ready**: Estrutura preparada para adicionar rate limiting

## Variáveis de Ambiente (opcional)

```env
SECRET_KEY=sua_chave_secreta_aqui
ACCESS_TOKEN_EXPIRE=30
REFRESH_TOKEN_EXPIRE=7
RESET_TOKEN_EXPIRE=1
```

## Testes

```bash
cd backend
pytest -v
```

## Notas

- O banco é SQLite em memória/arquivo (`auth.db`)
- Para produção, substitua por PostgreSQL/MySQL
- Emails de recuperação devem ser implementados com SMTP real
- Adicione rate limiting com `slowapi` para produção

---

Criado como projeto educacional completo de autenticação.
