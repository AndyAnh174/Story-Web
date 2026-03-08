# 📁 CẤU TRÚC DỰ ÁN (PROJECT STRUCTURE)

Dự án AI Co-Authoring SaaS được phát triển trên kiến trúc **Monorepo** (sử dụng công cụ Turborepo / Nx), cho phép quản lý toàn bộ cả khối Frontend (Next.js) lẫn khối Backend (FastAPI Python) chung trong cùng một Git Repository duy nhất.

Cấu trúc thư mục dưới đây được thiết kế để tối ưu hóa việc phân chia trách nhiệm, tái sử dụng các gói (packages) và dễ dàng triển khai (deployment) lên các container Docker.

---

## 1. Cấu Trúc Tổng Thể (Monorepo Root)

Khởi tạo tại thư mục gốc `d:/Story/Story-Web/`:

```text
Story-Web/
├── apps/                 # Chứa các ứng dụng độc lập có thể chạy được
│   ├── web/              # 💻 Web App chính cho Tác giả (Next.js 16)
│   └── api/              # 🧠 Core Backend AI & Logic (FastAPI Python)
├── packages/             # Các thư viện code dùng chung (sẽ được import vào apps)
│   ├── ui/               # Reusable Tailwind/Shadcn Components dùng cho Frontend (nếu cần)
│   ├── eslint-config/    # Luật dọn dẹp biến lint chuẩn cho JS/TS
│   └── tailwind-config/  # File config CSS dùng chung
├── docs/                 # Tài liệu thiết kế hệ thống (Information, Tech-stack, DB)
├── turbo.json            # File cấu hình của Turborepo để tối ưu tốc độ Build
├── package.json          # Root dependencies (pnpm workspaces)
├── pnpm-workspace.yaml   # Định nghĩa ranh giới các workspaces
└── docker-compose.yml    # File khởi chạy đồng loạt Web, API, Redis, Postgres local
```

---

## 2. Chi Tiết Khối Frontend (`apps/web/`)

Xây dựng bằng **Next.js 16 (App Router)** và **Clerk Auth**.

```text
apps/web/
├── app/                  # (App Router) Cấu trúc trang (Pages & Routing)
│   ├── (auth)/           # Route Group cho SignIn/SignUp (Clerk)
│   ├── (dashboard)/      # Khu vực quản lý danh sách truyện (Projects)
│   ├── workspace/        # 🎨 Màn hình Editor & Chat chính với AI
│   ├── api/              # API Routes phụ trợ của Next.js (nếu cần proxy gọi Clerk)
│   ├── globals.css       # File CSS Tailwind gốc
│   └── layout.tsx        # Layout tổng có nhúng <ClerkProvider>
├── components/           # UI Components chia nhỏ
│   ├── chat/             # Chat Bubbles, Input Bar 
│   ├── editor/           # Khung nhập liệu (Rich-text, Markdown)
│   └── layout/           # Sidebar, Navigation Bar
├── hooks/                # Custom React Hooks
│   └── use-chat-stream.ts# Xử lý kết nối Server-Sent Events (SSE) để chữ tự nhảy
├── lib/                  # Các hàm tiện ích (Utils)
│   ├── api.ts            # Axios instances gọi đến Backend FastAPI (Kẹp JWT Token)
│   └── utils.ts          # Các helper function (ví dụ: cn format class Tailwind)
├── types/                # Typescript Interfaces/Types định nghĩa Data
├── middleware.ts         # Middleware của Clerk chặn quyền truy cập (Protect Routes)
├── next.config.ts        # Config Next.js
├── tailwind.config.ts    # Config Tailwind
└── package.json          # File dependencies riêng của Web
```

---

## 3. Chi Tiết Khối Backend (`apps/api/`)

Xây dựng bằng **FastAPI (Python 3.13+)**, được chia theo mô hình **Router-Controller-Service** (Gần giống Clean Architecture) để code dễ bảo trì khi nghiệp vụ AI phình to.

```text
apps/api/
├── app/                  # Mã nguồn chính của FastAPI
│   ├── api/              # Khai báo các API Endpoints (Controllers)
│   │   ├── routes/       
│   │   │   ├── auth.py   # Router Xác thực (Verify Token từ Clerk)
│   │   │   ├── chat.py   # Router xử lý Chat API (Trả về Streaming SSE)
│   │   │   └── project.py# Router CRUD dự án truyện
│   │   └── deps.py       # Dependency Injection (Hàm get_db, auto-verify current_user)
│   ├── core/             # Cấu hình lõi của Server
│   │   ├── config.py     # Đọc biến môi trường (ENV) bằng Pydantic BaseSettings
│   │   └── security.py   # Logic giải mã JWKS Token lấy từ Clerk
│   ├── db/               # Tương tác Database Mạng nhện
│   │   ├── postgres/     # Models SQLAlchemy & Migrations (Alembic)
│   │   ├── neo4j/        # Client & Cypher Query Logic cho Graph
│   │   └── qdrant/       # Client & Embeddings Logic cho Vector
│   ├── schemas/          # Pydantic Models để Validate Input/Output (Request/Response)
│   ├── services/         # Nơi chứa MỌI Logic Nghiệp vụ (Core "Brain")
│   │   ├── ai_service.py # Gọi Ollama (gpt-oss:120b) tạo text
│   │   ├── rag_service.py# Hàm đi query 3 DB lấy bối cảnh gom thành System Prompt
│   │   └── context_extractor.py # Logic Background bóc tách Entity JSON
│   ├── workers/          # Background Tasks (Celery / RQ)
│   │   └── cleanup_job.py# Task chạy ngầm xóa Zombie Data
│   └── main.py           # 🚀 File Boot khởi chạy ứng dụng FastAPI (app = FastAPI())
├── tests/                # Unit Tests & Integration Tests (pytest)
├── alembic/              # Thư mục chứa các bản ghi lịch sử DB Migration (Postgres)
├── requirements.txt      # Danh sách thư viện Python (Hoặc file pyproject.toml nếu dùng uv)
└── Dockerfile            # Config đóng gói riêng cho Backend
```

---

## 4. Giải Pháp Giao Tiếp Frontend ↔ Backend (API Flow)

Vì sử dụng 2 ngôn ngữ và framework tách biệt, luồng giao tiếp bắt buộc tuân theo chuẩn sau:

1. **Frontend Authentication:** Người dùng đăng nhập qua mảng UI của **Clerk** gắn trên `apps/web`. Next.js không có quyền gọi DB.
2. **Frontend Request:** Người tác giả gõ *"Viết trích đoạn đánh nhau"*, Frontend Next.js dùng thư viện Axios/Fetch lấy JWT Session Token gắn vào HTTP Header `Authorization: Bearer <token>`, rồi bắn Post Request gõ thẳng vào cổng API của Python (VD: `http://localhost:8000/api/v1/chat`).
3. **Backend Verify:** File `deps.py` trong FastAPI bắt được Request, ngay lập tức bắt Header và mang lên endpoint public của Clerk để Verify Checksum Token đó xem có "chuẩn auth" không. Nếu ok => Parse ra ID Clerk để cấp phép truy cập vòng trong lấy `project_id`.
4. **Backend RAG & Stream:** FastAPI truy vấn DB, gọi Model AI (Ollama) và `yield` (trả về lũy tiến từng đoạn text Chunk) thông qua giao thức Server-Sent Events (SSE) để màn hình Next.js hiện chữ chạy rào rào.
