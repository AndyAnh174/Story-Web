# CLAUDE.md — Story AI Platform

Đây là hướng dẫn bắt buộc cho AI Assistant khi làm việc trong dự án này.
Đọc kỹ toàn bộ file này trước khi thực hiện bất kỳ thay đổi nào.

---

## 1. Tổng quan dự án

**AI Co-Authoring SaaS** — Nền tảng giúp tác giả viết truyện dài kỳ (tiểu thuyết, light novel) cùng AI.
Tác giả đóng vai "Đạo diễn cốt truyện", AI hỗ trợ sáng tác với trí nhớ nhân vật chính xác qua RAG đa tầng.

- **Docs chi tiết:** `docs/` (INFORMATION.md, FEATURE.md, TASK.md, DATABASE.md, TECH-STACK.md, LOGIC-PROCCESS-DATA.md, STRUCTER-PROJECT.md)
- **Monorepo root:** `Story-Web/`
- **Frontend:** `Story-Web/apps/web/` (Next.js)
- **Backend:** `Story-Web/apps/api/` (FastAPI)
- **Môi trường:** `Story-Web/apps/environment/`

---

## 2. Tech Stack

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · shadcn/ui (@base-ui/react) |
| Auth | Clerk (JWT — Frontend + Backend đều verify độc lập) |
| Backend | FastAPI (Python 3.13+) · Pydantic v2 · SQLAlchemy 2.0 async |
| AI Gen | Ollama local — model `gpt-oss:120b-cloud` tại `http://localhost:11434` |
| AI Embed | Ollama — model `bge-m3:567m` tại `http://222.253.80.30:11434/api/embeddings` |
| AI Orchestration | LangChain / LangGraph |
| DB Chính | PostgreSQL + Alembic migrations |
| Vector DB | Qdrant — collection `project_memories` |
| Graph DB | Neo4j |
| Queue | Redis + Celery |
| Package Manager | `pnpm` (Node) · `uv` hoặc `pip` (Python) |

---

## 3. Quy tắc bắt buộc (KHÔNG được vi phạm)

### 3.1 Multi-tenancy
- **MỌI** truy vấn Database đều PHẢI kèm `user_id` VÀ `project_id`.
- Neo4j: Mọi Node và Relationship PHẢI có property `project_id`. Mọi Cypher query PHẢI có `WHERE n.project_id = $project_id`.
- Qdrant: Mọi vector upsert/query PHẢI có payload filter `project_id`.
- PostgreSQL: Mọi query PHẢI join hoặc filter theo `user_id` → `project_id`.

### 3.2 Xóa dữ liệu (Soft-delete First)
- Khi user xóa Project/Chat/Chapter: **CHỈ** set `is_deleted = TRUE` trong Postgres, trả về `200 OK` ngay.
- Celery background job mới chịu trách nhiệm hard-delete Neo4j nodes + Qdrant vectors.
- **KHÔNG BAO GIỜ** xóa thẳng Neo4j/Qdrant từ API request đồng bộ.

### 3.3 Auth
- Mọi FastAPI endpoint cần bảo vệ đều PHẢI dùng `Depends(get_current_user)`.
- `get_current_user` verify JWT từ Clerk qua JWKS — xem `app/api/dependencies/auth.py`.
- Frontend dùng `useFetchApi()` hook để tự động đính kèm Clerk token vào mọi API call.

### 3.4 TypeScript / Python typing
- TypeScript: **Strict mode**, không dùng `any` trừ khi bất khả kháng.
- Python: **Pydantic v2** cho tất cả schema input/output. Type hint đầy đủ.

---

## 4. Kiến trúc Frontend (`apps/web/`)

### Cấu trúc thư mục
```
src/
├── app/
│   ├── dashboard/          # Khu vực chính sau đăng nhập
│   │   ├── layout.tsx      # Sidebar + top header (Glassmorphism)
│   │   ├── page.tsx        # Tổng quan (metrics)
│   │   └── projects/
│   │       ├── page.tsx    # Danh sách dự án truyện
│   │       └── [id]/
│   │           └── graph/
│   │               └── page.tsx  # Visual Graph Map
│   ├── chat/[id]/page.tsx  # Chat với AI
│   ├── sign-in/ sign-up/   # Clerk auth pages
│   └── layout.tsx          # Root (ClerkProvider)
├── components/
│   ├── ui/                 # shadcn/ui components (Button, Card, Dialog, Input...)
│   └── graph/              # Visual Graph components (@xyflow/react)
│       ├── types.ts        # GraphNode, GraphEdge types + mock data
│       ├── GraphCanvas.tsx # React Flow canvas (PHẢI dynamic import, ssr: false)
│       ├── GraphToolbar.tsx
│       ├── NodeDetailPanel.tsx
│       ├── GraphLegend.tsx
│       └── nodes/          # PersonNode, LocationNode, SkillNode, EventNode, ItemNode
├── hooks/
│   └── use-fetch-api.ts    # Clerk-authenticated API calls
└── lib/utils.ts            # cn() utility
```

### UI Pattern — Glassmorphism (dùng nhất quán)
```tsx
// Panel / Sidebar
bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl
border-slate-200/50 dark:border-slate-800/50

// Card
bg-white/40 backdrop-blur-md border-slate-200/50 shadow-sm
dark:bg-slate-900/40 dark:border-slate-800/50

// Message bubble (AI)
bg-white/90 backdrop-blur-sm dark:bg-slate-900/90
ring-1 ring-inset ring-slate-900/5 dark:ring-white/5
```

### Lưu ý quan trọng
- Components dùng `@base-ui/react` primitives — KHÔNG phải Radix UI.
- Mọi component interactive cần `"use client"` directive.
- `params` trong Next.js 15+ là `Promise` — dùng `use(params)` trong client components.
- React Flow (`@xyflow/react`) BẮT BUỘC dynamic import với `{ ssr: false }`.

---

## 5. Kiến trúc Backend (`apps/api/`)

### Cấu trúc thư mục mục tiêu
```
app/
├── api/
│   ├── routes/
│   │   ├── auth.py         # Verify token endpoint
│   │   ├── chat.py         # SSE streaming chat
│   │   └── project.py      # CRUD dự án
│   └── dependencies/
│       └── auth.py         # get_current_user (Clerk JWT verify)
├── core/
│   ├── config.py           # Settings (pydantic BaseSettings)
│   └── security.py
├── db/
│   ├── postgres/           # SQLAlchemy session + base
│   ├── neo4j/              # Driver + Cypher helpers
│   └── qdrant/             # Client + embedding helpers
├── models/
│   └── core_models.py      # SQLAlchemy ORM models
├── schemas/                # Pydantic v2 request/response schemas
├── services/
│   ├── ai_service.py       # Gọi Ollama gen text
│   ├── rag_service.py      # Query 3 DB → System Prompt
│   └── context_extractor.py# Entity extraction → Neo4j
└── workers/
    └── cleanup_job.py      # Celery soft-delete cleanup
```

### Database Models (PostgreSQL)
- `users`: id (Clerk ID), email, name, created_at
- `projects`: id, user_id (FK), title, description, is_deleted, created_at, updated_at
- `chats`: id, project_id (FK), title, is_deleted, created_at
- `chat_messages`: id, chat_id (FK), role (user/ai/system), content, created_at
- `chapters`: id, project_id (FK), title, order_index, content, is_deleted
- `lorebooks`: id, project_id (FK), keyword, category, description, fts_vector (tsvector)

---

## 6. RAG Pipeline (luồng cốt lõi)

```
User gửi prompt
    ↓
FastAPI verify JWT (Clerk) → lấy user_id + project_id
    ↓
[Song song Async]
├── Postgres: FTS tìm Lorebook (tsvector MATCH keyword)
├── Qdrant: Similarity search văn phong (filter: project_id)
└── Neo4j: Graph traversal — nhân vật, trạng thái sống/chết (WHERE project_id)
    ↓
Ráp System Prompt (Neo4j context + Lorebook + Qdrant văn phong)
    ↓
gpt-oss:120b-cloud → Stream SSE về Frontend
    ↓
User "Chốt" → Lưu Postgres → Push Celery job
    ↓
[Background] LLM extract JSON entities → Neo4j mutation + Qdrant embed
```

### System Prompt chuẩn RAG
```
[SYSTEM]
Bạn là Đạo diễn Cốt truyện. Project: {project_title}

### 1. TRẠNG THÁI NHÂN VẬT (Neo4j)
- {name}: STATUS={Alive/Dead}, Skills=[...], Faction=[...]
- CẤM: Nhân vật Dead không được xuất hiện/hành động.

### 2. LOREBOOK (Postgres FTS)
- {keyword}: {definition}

### 3. VĂN PHONG TRƯỚC (Qdrant)
{qdrant_chunks}

### YÊU CẦU: Viết tiếp, tuân thủ tuyệt đối logic trên.
```

---

## 7. Tiến độ dự án (cập nhật: 2026-03-09)

| Giai đoạn | Trạng thái |
|---|---|
| 1. Scaffolding & Docs | ✅ Xong |
| 2. DB Connections + Auth | ✅ Xong |
| 3. Frontend UI cơ bản (Dashboard, Chat) | ✅ Xong |
| 3.5. Visual Graph Map UI | ✅ Xong |
| 4. RAG Services (Embeddings, rag_service, Neo4j query) | ❌ Chưa làm |
| 5. Streaming Chat SSE + Celery + Entity Extractor | ❌ Chưa làm |
| 6. Soft-delete API + Cleanup Job | ❌ Chưa làm |

**Next task:** Giai đoạn 4 — xây `rag_service.py`, `ai_service.py`, API `/chat` với SSE.

---

## 8. Biến môi trường quan trọng

**Frontend** (`apps/web/.env.local`):
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
CLERK_SECRET_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Backend** (`apps/api/.env`):
```
DATABASE_URL=postgresql+asyncpg://...
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
REDIS_URL=redis://localhost:6379/0
CLERK_SECRET_KEY=...
OLLAMA_GEN_HOST=http://localhost:11434
OLLAMA_MODEL_GEN=gpt-oss:120b-cloud
OLLAMA_EMBED_HOST=http://222.253.80.30:11434/api/embeddings
OLLAMA_MODEL_EMBED=bge-m3:567m
```

---

## 9. Lệnh thường dùng

```bash
# Chạy Frontend
cd Story-Web && pnpm --filter web dev

# Chạy Backend
cd Story-Web/apps/api && uvicorn main:app --reload --port 8000

# Alembic migration
cd Story-Web/apps/api && alembic upgrade head

# Docker (databases local)
cd Story-Web/apps/environment && docker compose -f docker-compose.dev.yml up -d

# TypeScript check
cd Story-Web/apps/web && pnpm tsc --noEmit
```
