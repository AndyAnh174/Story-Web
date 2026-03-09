---
trigger: always_on
---

# 🧠 QUY TẮC SỬ DỤNG KỸ NĂNG CỦA AI (SKILL USAGE RULES)

Với tư cách là System Agent (Tên: Antigravity), bạn được trang bị một hệ thống tệp tin kỹ năng (`SKILL.md`) cực kỳ đồ sộ. Dưới đây là quy định bắt buộc về việc **KHI NÀO** phải gọi tính năng đọc (`view_file`) các `SKILL.md` để "nạp kiến thức" trước khi code.

## 1. Nguyên Tắc Cốt Lõi (Core Principles)
1. **Không code dựa trên trí nhớ chung:** Công nghệ Web và Lib thay đổi liên tục. Nếu thấy tác vụ có vẻ "khớp" với một Skill đã cài đặt, AI **BẮT BUỘC** đọc `SKILL.md` của thư mục đó trước để lấy Syntax/Pattern mới nhất.
2. **Kích hoạt Ngữ Cảnh (Context Activation):** Khi tác giả bắt đầu một phiên làm việc mới, AI phải tự hỏi: *"Tác giả đang đụng vào thành phần nào của dự án?"* để load Skill tương ứng.

---

## 2. Bảng Phân Bổ Skill Theo Lớp Kiến Trúc (Layer Mapping)

### 2.1. Lớp Backend (FastAPI - `apps/api/`)
Trường hợp đụng vào thư mục Backend, AI phải đọc nhóm Skill:
- **`fastapi-pro`** (Kỹ thuật async API, SQLAlchemy 2.0).
- **`python-pro`** (Các pattern tối ưu hiệu năng Python 3.12+).
- **`backend-architect`** (Khi cần thiết kế thêm Endpoint phức tạp).

### 2.2. Lớp Frontend (Next.js - `apps/web/`)
Khi Tác giả yêu cầu làm UI, chia Component, hay ghép Call API:
- **`frontend-developer`** (Quy tắc React 19/Next 15 tối ưu).
- **`nextjs-app-router-patterns`** (Pattern định tuyến Server Components/Client Components).
- **`tailwind-design-system`** (Quy tắc chia biến CSS, xây cấu trúc UI xịn xò mang phong cách Magic UI / Shadcn).
- **`clerk-nextjs-skills`** (Mọi thay đổi liên quan đến phân quyền/Session của user mặt Frontend).

### 2.3. Lớp Database & DB Kiến trúc RAG
Khi phải viết Script chỉnh sửa, Update cấu trúc hay tối ưu Query DB:
- **`database-architect`** / **`postgresql-table-design`** (Khi dựng Schema có Khóa ngoại Postgres).
- **`rag-implementation`** / **`hybrid-search-implementation`** (Nguyên lý RAG cho Vector DB Qdrant).

### 2.4. Lớp AI Agent & Prompt Engineering (Lõi Trí Nhớ)
Khi nhận yêu cầu tinh chỉnh logic "Trí nhớ nhân vật" hoặc viết lại prompt đút cho Model (Ollama gpt-oss):
- **`prompt-engineer`** (Viết lại System Prompt sắc bén, chống OOC).
- **`langchain-architecture`** (Ghép nối mảng Chain logic Extract JSON -> Update Neo4j -> Query RAG -> Gen text).

---

## 3. Lệnh Cấm Kỵ (Do Nots)
- ❌ **Không** được mix lộn xộn các skill khác hệ (Vd: Dùng skill `authjs-skills` khi dự án đã quy định dùng `clerk-nextjs-skills`).
- ❌ **Không** tự đẻ ra pattern code mới nến đụng vào component có thể sử dụng Design Pattern trong `architecture-patterns` hoặc kiến thức của Monorepo (`monorepo-architect`).
