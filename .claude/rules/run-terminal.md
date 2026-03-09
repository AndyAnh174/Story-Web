---
trigger: always_on
---

# Terminal Execution Rules cho Hệ Thống AI Co-Authoring SaaS

Tài liệu này quy định các quy tắc khắt khe khi AI (hoặc Assistant) thực thi lệnh Terminal (run_command) cho dự án Monorepo này. Bắt buộc phải tuân theo 100%.

## 1. 🐍 Quy Tắc Chạy Backend (Python - FastAPI)
`Path Target: d:/Story/Story-Web/apps/api`

1. **Môi Trường Ảo (Virtual Environment):**
   - MỌI lệnh thực thi Python (như chạy server, cài thư viện, run script) ĐỀU PHẢI được gọi thông qua môi trường ảo (Virtual Env).
   - Trên Windows, đường dẫn khởi chạy sẽ bắt đầu bằng: `.\venv\Scripts\python` hoặc `.\venv\Scripts\pip`.
   - **Tuyệt đối KHÔNG** gõ lệnh `python` hoặc `pip` trơn tuột trên terminal gốc để tránh làm rác môi trường toàn cục (Global Environment).

2. **Cách Khởi Chạy FastAPI:**
   - Khi cần khởi chạy Server Backend để test API, BẮT BUỘC dùng lệnh CLI mới nhất của FastAPI:
   - Lệnh quy chuẩn: `.\venv\Scripts\fastapi dev main.py` (hoặc đường dẫn tới file main). Không dùng `uvicorn` thủ công trừ khi có cấu hình đặc thù.

3. **Kích Hoạt Kỹ Năng (Skills) Tương Đương:**
   - Khi thao tác sửa/thêm code Backend, AI phải ưu tiên rà soát (dùng view_file) và áp dụng các kinh nghiệm từ hệ thống `python-pro`, `fastapi-pro`, `backend-architect`, `database-architect` đã được cài sẵn.

---

## 2. ⚛️ Quy Tắc Chạy Frontend (Next.js)
`Path Target: d:/Story/Story-Web/apps/web`

1. **Trình Quản Lý Gói (Package Manager):**
   - MỌI thao tác cài thư viện (install/add), chạy script (run dev/build) ở Frontend ĐỀU PHẢI dùng lệnh **`pnpm`**.
   - **Tuyệt đối KHÔNG** dùng `npm`, `yarn` hay `bun` để giữ tính đồng nhất của lockfile.

2. **Kích Hoạt Kỹ Năng (Skills) Tương Đương:**
   - Khi chỉnh sửa giao diện, AI phải ưu tiên sử dụng các Design Pattern hiện đại từ những bộ kỹ năng: `frontend-developer`, `nextjs-app-router-patterns`, `clerk-nextjs-skills`, `tailwind-design-system`.
