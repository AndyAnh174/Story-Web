# 📋 DANH SÁCH NHIỆM VỤ (PROJECT MASTER TASK LIST)

Dự án AI Co-Authoring SaaS Platform (LLMOps cho Tác giả).
Tiến độ được đánh dấu theo chuẩn Markdown: `[ ]` (Chưa làm), `[/]` (Đang làm), `[x]` (Hoàn thành).

---

## GIAI ĐOẠN 1: KHỞI TẠO CẤU TRÚC (SCAFFOLDING & DOCS)
- [x] Lên quy chuẩn kiến trúc (INFORMATION, TECH-STACK)
- [x] Thiết kế Database Schema (Postgres, Qdrant, Neo4j)
- [x] Viết logic RAG & Trí nhớ nhân vật (LOGIC-PROCCESS-DATA)
- [x] Chốt cấu trúc thư mục Monorepo (STRUCTER-PROJECT)
- [x] Setup file luật cho AI (.agent/rules)
- [x] Setup Docker Compose rỗng cho Local Environment (Postgres, Qdrant, Neo4j, Redis)
- [x] Khởi tạo khung rỗng FastAPI Backend (`apps/api`)
- [x] Khởi tạo khung Frontend Next.js 16 (`apps/web` với pnpm)

---

## GIAI ĐOẠN 2: KẾT NỐI DATABASE VÀ AUTH (BACKEND FOUNDATION)
- [x] Thiết lập Connection Pool với PostgreSQL (SQLAlchemy Async).
- [x] Thiết lập Connection với Qdrant Client.
- [x] Thiết lập Connection với Neo4j Driver.
- [x] Viết mô hình Database Models (Users, Projects, Chats, Lorebooks) cho SQLAlchemy.
- [x] Chạy Alembic Migration lần đầu để tạo bảng trong Postgres.
- [x] Viết API Middleware để Verify JWKS (JSON Web Key Set) từ Clerk.

---

## GIAI ĐOẠN 3: XÂY DỰNG FRONTEND NEXT.JS CƠ BẢN (AUTHENTICATION & UI)
- [x] Thiết lập biến môi trường Clerk `.env.local`.
- [x] Tạo UI Đăng nhập / Đăng ký tại `apps/web/src/app/(auth)`.
- [x] Thiết lập `proxy.ts` (Next.js Middleware) để bảo vệ route (ngoại trừ `/sign-in`, `/sign-up`, `/`).
- [x] Viết Hook Frontend (`useFetchApi`) để đính kèm Token xác thực vào API Request.
- [x] Tạo màn hình UI cơ bản (`/dashboard`) theo phong cách Glassmorphism.
- [x] Xây dựng Layout màn hình Chat (Sidebar, Chat Window, Settings).

---

## GIAI ĐOẠN 3.5: VISUAL GRAPH UI (Bản đồ Thực thể)
- [x] Cài @xyflow/react + @dagrejs/dagre vào `apps/web`
- [x] Tạo TypeScript types & mock demo data (Kurama, Kento, Raito...)
- [x] Xây 5 custom Node components (Person/Location/Skill/Event/Item) - Glassmorphism style
- [x] GraphCanvas với auto-layout dagre, MiniMap, Controls
- [x] GraphToolbar: Add node buttons + Tự xếp
- [x] NodeDetailPanel: Slide-in panel View/Edit, xóa node
- [x] GraphLegend: Chú thích màu sắc node types & relationship
- [x] Trang `/dashboard/projects/[id]/graph` - 2 mode View/Edit
- [x] Trang `/dashboard/projects` - Danh sách dự án truyện
- [x] Thêm "Bản đồ truyện" vào Dashboard sidebar

---

## GIAI ĐOẠN 4: LUỒNG RAG & TRÍ NHỚ ĐA TẦNG (CORE AI)
- [ ] Viết API Sinh Vector (Embeddings) gọi endpoint Model BGE-M3.
- [ ] Viết Service `rag_service.py`: Lấy Lorebook từ Postgres (tsvector).
- [ ] Viết Service truy vấn bối cảnh văn phong từ Qdrant (Similarity Search).
- [ ] Viết Service lấy trạng thái nhân vật / Skill từ Neo4j (Cypher Query).
- [ ] Ráp toàn bộ nội dung thành System Prompt gửi cho Model `gpt-oss:120b`.

---

## GIAI ĐOẠN 5: STREAMING CHAT & BACKGROUND JOB 
- [ ] Dựng API endpoint `/chat` trả về Server-Sent Events (SSE) để chữ nhảy mượt trên UI.
- [ ] Tích hợp React Hook `use-chat-stream` trên Frontend đón luồng SSE.
- [ ] Cấu hình Celery (gắn với Redis) tạo Background Job.
- [ ] Viết Tool Function cho LLM bóc tách JSON (Entity Extractor: Live/Dead, Skills...).
- [ ] Viết Logic lặp Cypher cập nhật Node mới, đổi status Node cũ nhét thẳng vào Neo4j sau mỗi câu Chat.

---

## GIAI ĐOẠN 6: LUỒNG QUẢN LÝ THAY ĐỔI / DỌN RÁC
- [ ] Viết API xoá Chat/Project (Cập nhật `is_deleted = TRUE` trên Postgres).
- [ ] Viết Celery Cleanup Job đi dọn Node dư trên Neo4j & xoá Vector dư trên Qdrant.
- [ ] Test luồng Self-Correction: Thử cho LLM nhắc lại Kento sau khi Kento chết để xem hệ thống có tự Reject không.
