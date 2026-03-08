# 🛡️ TECH STACK: AI Co-Authoring SaaS Platform

Dựa trên kiến trúc tổng thể từ `INFORMATION.md`, dưới đây là danh sách chi tiết các công nghệ (Tech Stack) được sử dụng trong dự án, phân bổ theo từng Layer.

---

## 1. Môi trường & Quản trị Mã nguồn (Workspace & CI/CD)
- **Monorepo Manager:** Turborepo / Nx (Quản lý đa dự án Frontend/Backend chung một code base).
- **Containerization:** Docker & Docker Compose (Đóng gói và triển khai đồng bộ).
- **Hệ điều hành Server:** Debian / Proxmox (Virtualization).
- **Package Manager:** `pnpm` (cho Node.js) và `uv` hoặc `poetry` (cho Python).
- **CI/CD:** GitHub Actions (hoặc GitLab CI).

---

## 2. Frontend Layer (Tương tác Tác giả)
- **Core Framework:** Next.js v16.1.6 (App Router).
- **Language:** TypeScript (Strict Mode).
- **Styling:** Tailwind CSS (kết hợp các UI Component hiện đại như Shadcn UI, Magic UI).
- **Authentication:** Clerk (Quản lý người dùng, Login Google/Email, Session & Token phân quyền).
- **State Management:** Zustand (Global State) + React Query / SWR (Server State & Caching).
- **Data Fetching:** Fetch API chuẩn Next.js & Server Actions.

---

## 3. Backend Layer (Logic & Điều phối AI)
- **Core Framework:** FastAPI (Python 3.13+).
- **Language:** Python (Strict Typing với Pydantic v2).
- **API Architecture:** RESTful API & Server-Sent Events (SSE) cho luồng Stream Chat.
- **Background Jobs:** Celery hoặc RQ (Redis Queue) để xử lý tác vụ nặng (Sinh text dài, dọn dẹp dữ liệu DB).
- **Message Broker & Caching:** Redis.
- **AI Orchestration Framework:** LangChain / LangGraph (Quản lý luồng Agent và Prompt).

---

## 4. AI Models & Endpoints Layer (Tính toán Ngôn ngữ & Vector)
- **Text Generation (Sinh văn bản):** Model `gpt-oss:120b-cloud` (Chạy local qua Ollama tại endpoint `http://localhost:11434/`).
- **Vector Embeddings (Mã hóa ngữ nghĩa):** Model `bge-m3:567m` (Chạy local qua Ollama tại endpoint `http://222.253.80.30:11434/api/embeddings`).

---

## 5. Database Layer (Lưu trữ Đa tầng - Multi-tenant)
- **Primary Database (Relational & Full-text):** PostgreSQL.
  - *Chức năng:* Lưu Users, Projects, Chats, Chapters. 
  - *Đặc biệt:* Dùng tính năng `tsvector` để tìm kiếm Full-text bộ thuật ngữ Lorebook.
  - *ORM:* SQLAlchemy 2.0.
- **Vector Database (Semantic Search):** Qdrant.
  - *Chức năng:* Lưu trữ các embeding của ngữ cảnh truyện, phân loại qua payload `{user_id, project_id}`.
- **Graph Database (Knowledge Graph):** Neo4j.
  - *Chức năng:* Lưu trữ sơ đồ quan hệ nhân vật, phân tách Multi-tenant bằng thuộc tính `project_id` bắt buộc trên mọi Node và Relationship.

---

## 6. Tiêu chuẩn Mã nguồn (Coding Standards)
- **Frontend:** ESLint, Prettier, Husky (Pre-commit hooks).
- **Backend:** Ruff (Linter & Formatter), Mypy (Type Checking).
- **Bảo mật:** Verify JWT Token (từ Clerk) trên mọi Endpoint của FastAPI yêu cầu xác thực.
