# ✍️ AI Co-Authoring SaaS Platform

Dự án **AI Co-Authoring SaaS Platform** là một nền tảng hỗ trợ sáng tác tiểu thuyết (đặc biệt là thể loại Tiên Hiệp, Huyền Huyễn) dưới dạng Phần mềm như một Dịch vụ (SaaS). 

Hệ thống kết hợp sức mạnh của Mô hình Ngôn ngữ Lớn (LLM - *gpt-oss 120b*) cùng kiến trúc Advanced RAG (Retrieval-Augmented Generation) 3 tầng cơ sở dữ liệu để giúp tác giả luôn **giữ vững văn phong** và **không bao giờ quên cốt truyện, nhân vật**.

---

## 🌟 Chức năng Cốt lõi (Core Features)

1. **Quản lý Truyện Đa Dự Án (Multi-tenancy):** Tác giả có thể tạo và quản lý nhiều bộ truyện riêng biệt. Dữ liệu của mỗi dự án được cách ly hoàn toàn để đảm bảo tính cá nhân hóa.
2. **Giao diện Chat Định Hướng Sáng Tác:** Trò chuyện trực tiếp với AI để tìm ý tưởng, phát triển nhân vật, chia nhánh cốt truyện với UI Glassmorphism hiện đại (Next.js + Tailwind).
3. **Trí Nhớ Đồ Thị (Neo4j Graph Memory):** AI tự động chạy ngầm trích xuất mối quan hệ nhân vật (VD: Ai là sư phụ của ai, ai có thù với ai) để chống "râu ông nọ cắm cằm bà kia". Đặc biệt có **Giao diện Visual Map** để nhìn toàn cảnh cốt truyện.
4. **Bảo Tồn Văn Phong (Qdrant Vector DB):** Tính năng băm (chunk) các chương truyện đã viết để lưu vào CSDL Vector. Nhờ đó AI luôn mô phỏng chính xác giọng văn và nhịp độ của chính tác giả.
5. **Từ Điển Cốt Truyện (PostgreSQL Lorebook):** Nơi tác giả tự định nghĩa hệ thống cảnh giới, chiêu thức, quy luật phép thuật để AI tra cứu thời gian thực (Full-text Search).
6. **Bảo mật tối đa (Clerk Auth):** Xác thực người dùng bằng Google/Email, tích hợp Session lưu trữ an toàn đến tận lớp Backend (FastAPI JWT Middleware).

👉 Xem chi tiết tại: `docs/FEATURE.md`

---

## 🏗️ Kiến Trúc Hệ Thống (Architecture & Tech Stack)

Dự án sử dụng mô hình **Turborepo (Monorepo)** phân tách rõ ràng giữa Frontend và Backend.

### 🌐 1. Frontend: Next.js App Router (`apps/web`)
* **Framework:** Next.js 16 (App Router) + TypeScript.
* **UI & Styling:** Tailwind CSS, Shadcn UI, Magic UI, Lucide Icons.
* **Authentication:** Clerk (@clerk/nextjs).
* **State & Fetching:** React Hooks, `useFetchApi` (Custom hook chặn JWT token).

### ⚙️ 2. Backend: FastAPI Python (`apps/api`)
* **Framework:** FastAPI (Python 3.12+).
* **AI Orchestration:** LangChain (Điều phối LLM, Tools, Streaming).
* **Worker Queue:** Celery + Redis (Xử lý các tác vụ RAG chạy ngầm tốn thời gian).

### 🗄️ 3. Database Layer (Advanced RAG Strategy)
* **PostgreSQL:** Lưu trữ Metadata (Users, Projects, Chats, Chapters, Lorebook). Tích hợp `tsvector` cho tìm kiếm cực nhanh.
* **Neo4j DB:** Knowledge Graph (Tìm kiếm và bảo vệ Logic truyện).
* **Qdrant DB:** Vector Search (Tìm kiếm ngữ nghĩa và lưu giữ Văn Phong).

👉 Xem chi tiết tại: `docs/TECH-STACK.md` và `docs/DATABASE.md`

---

## 🚀 Hướng Dẫn Cài Đặt (Local Development)

### Yêu cầu tiên quyết (Prerequisites):
* Node.js v20+ & `pnpm`
* Python 3.12+ (khuyên dùng `uv` hoặc `venv`)
* Docker & Docker Compose (Để Spin-up 3 Databases & Redis)
* Tài khoản Clerk (Tạo Project và cấu hình Keyless/Test Keys)

### Bước 1: Khởi động Đội hình Database & Message Broker
Chạy script Docker để khởi tạo môi trường (DB & Redis):
```bash
cd apps/environment
docker-compose -f docker-compose.dev.yml up -d
```
*Các dịch vụ sẽ chạy tại:* 
- Postgresql: `localhost:5432`
- Qdrant: `localhost:6333`
- Neo4j: `localhost:7687` (Bolt) / `7474` (UI)
- Redis: `localhost:6379`

### Bước 2: Setup Frontend (Next.js)
```bash
# 1. Cài đặt các gói phụ thuộc
pnpm install

# 2. Cấu hình biến môi trường
# Mở file `apps/web/.env.local`
# Thêm `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` và `CLERK_SECRET_KEY`

# 3. Chạy Dev Server
cd apps/web
pnpm dev
# Ứng dụng chạy tại: http://localhost:3000
```

### Bước 3: Setup Backend (FastAPI)
```bash
# 1. Di chuyển vào thư mục api
cd apps/api

# 2. Kích hoạt môi trường ảo Python
python -m venv venv
.\venv\Scripts\activate  # (Trên Windows)
# hoặc
source venv/bin/activate # (Trên Mac/Linux)

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Sao chép và cấu hình biến môi trường
# Copy `apps/api/.env` vào chứa thông tin DB và `CLERK_SECRET_KEY` (Để giải mã JWT)

# 5. Chạy ASGI Server
fastapi dev main.py
# API Docs (Swagger) tự động sinh tại: http://localhost:8000/docs
```

---

## 📂 Cấu trúc Thư Mục (Directory Layout)

```text
Story-Web/
├── apps/
│   ├── api/                # Backend Python FastAPI
│   │   ├── app/            # Source Code
│   │   ├── requirements.txt
│   │   └── main.py
│   ├── environment/        # Docker Compose config cho Databases
│   └── web/                # Frontend Next.js 16
│       ├── src/
│       │   ├── app/        # App Router Pages
│       │   ├── components/ # Shadcn UI / Magic UI
│       │   └── hooks/      # React Custom Hooks
│       ├── proxy.ts        # Clerk Middleware (Auth)
│       └── tailwind.config.ts
├── docs/                   # Tài liệu thiết kế Schema, Tech Stack
├── packages/               # Thư mục chia sẻ UI/Config (Turborepo)
├── .gitignore              # Monorepo ignore
└── turbo.json
```

---
*Developed with AI-Assisted Architecture.*
