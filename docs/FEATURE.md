# 🌟 TỔNG HỢP TÍNH NĂNG (FEATURES) MỤC TIÊU: AI Co-Authoring SaaS

Tài liệu này liệt kê toàn bộ các tính năng lớn nhỏ mà hệ thống phần mềm SaaS Hỗ trợ Viết Truyện (AI Co-Authoring) cần phải đạt được. Đây sẽ là kim chỉ nam để rà soát tiến độ dự án.

---

## 🔒 1. Phân Hệ Quản Lý Tài Khoản & Workspace (Auth & Users)
**Công nghệ:** Clerk Auth, Next.js, PostgreSQL.

*   [x] **Đăng ký / Đăng nhập (Authentication):** Hỗ trợ Email/Password và Social Login (Google, GitHub) thông qua Clerk.
*   [x] **Quản lý Session:** Token JWT tự động luân chuyển giữa Next.js Frontend và cấu hình giải mã tại FastAPI Backend.
*   [x] **Tenant Isolation (Bảo vệ dữ liệu chéo):** Mọi API Request gắn liền với `user_id` hiện tại để trích xuất hoặc xóa dự án an toàn.
*   [x] **Trang cá nhân & Setting thông báo cơ bản** (Clerk UserButton).

## 📚 2. Phân Hệ Quản Trị Dự Án Truyện (Story Project Manager)
**Công nghệ:** Nhánh Frontend Dashboard, Component Shadcn, PostgreSQL Tabular.

*   [x] **Tạo mới bộ truyện (Create Project):** Đặt tựa đề, thêm mô tả tóm tắt.
*   [x] **Listing:** Bảng điều khiển (Dashboard) hiển thị danh sách các tác phẩm đang viết dở, trạng thái số chữ, số chương hiện tại.
*   [x] **Phân quyền truy cập đa nền tảng (Gỡ bỏ / Xóa dự án)**, triển khai Soft-delete đảm bảo an toàn cho History.

## 📝 3. Phân Hệ Đổi Thoại Cùng AI (AI Chat Interface)
**Công nghệ:** Next.js App Router, Tailwind Glassmorphism UI, LLM Stream (gpt-oss).

*   [x] **Giao diện Nhắn Tin:** Thiết kế tương tự siêu trí tuệ Chat-GPT nhưng nhắm tới mục tiêu sáng tác nghệ thuật. Tách rời hai bên Sidebar lịch sử chat và Main Chat Window.
*   [x] **Biên tập Chat:** Tạo phiên mới, xem lại phiên cũ hoặc xóa đoạn hội thoại không vừa ý.
*   [ ] **Tự động Gợi ý Mở bài / Tình huống (Prompt Snippets):** Click nhanh để "Yêu cầu rẽ nhánh cốt truyện", "Vẽ thêm một nhân vật phản diện ranh mãnh". 
*   [x] **Panel Tùy chỉnh Sinh Text (AI Settings):** Pop-up điều chỉnh Temperature (độ sáng tạo), Context length.

## 🧠 4. Phân Hệ Bộ Nhớ "Sống" Của Truyện (Trí nhớ Nhân Vật - Neo4j)
**Công nghệ:** FastAPI, Neo4j Graph Database.

*   [ ] **Trích xuất thực thể theo thời gian thực (Entity Extraction):** Trong lúc tác giả đang chat với AI để sáng tác hoặc lúc lưu thông tin cấu hình tay, AI tự chạy ngầm trích xuất Nhân vật (Person), Địa điểm (Location), Nhánh tình tiết (Event), Bí kíp (Skill), Đồ vật (Item) cất vào Graph.
*   [ ] **Nhắc Tuồng Bối Cảnh (Graph RAG Retrieval):** Khi tác giả gõ *"Nam chính đi vào sảnh"*, Graph tự động nội suy xem nam chính đang quen biết ai, thù ai ở cái sảnh đó để mớm vào System Prompt cho AI viết tiếp không bị sai Logic (Râu ông nọ cắm cằm bà kia).
*   [x] **Bản Đồ Mạng Lưới Nhãn Quan (Visual Graph Map):** Giao diện UI đồ hoạ để tác giả xem toàn cảnh sự liên kết mạng nhện giữa các nhân vật (Ai thù ai, ai yêu ai) và các mảnh ghép cốt truyện (Bang phái, Địa điểm) tương tự như mô hình Obsidian Graph View. **[DONE: `/dashboard/projects/[id]/graph`, dùng @xyflow/react + dagre layout, 2 mode View/Edit, 5 node types, NodeDetailPanel]**

## 🏹 5. Phân Hệ Giữ Vững Văn Phong Đã Viết (Văn Phong - Qdrant Vector)
**Công nghệ:** Tốc độ Vector Search Qdrant, Model bge-m3:567m.

*   [ ] **Auto-chunking Chương Truyện (Băm nhỏ):** Mỗi lần tác giả chốt xong 1 chương, Backend tự động băm text ra thành nhiều đoạn nhỏ và Embeddings sang Qdrant.
*   [ ] **Hybrid Vector Search:** Tìm kiếm ngữ nghĩa (VD gõ: "Đoạn main đánh rồng ở núi sập") -> Sẽ moi lên đúng đoạn mô tả cũ để lấy Văn Phong (Tone of Voice).
*   [ ] **Tự Động Mớm Văn Phong vào Mọi Lệnh Sáng Tác mới:** Việc tạo sinh câu chữ luôn mang âm hưởng cũ của chính tác giả.

## 📖 6. Phân Hệ Quản Lý Lorebook - Cẩm Nang Đọc Ké (Postgres FTS)
**Công nghệ:** PostgreSQL `tsvector`, Regex Tiếng Việt.

*   [ ] **Tạo Từ Điển Danh Tính Nhanh:** Tác giả tự định nghĩa các Cấp Bậc Tu Tiên (Luyện Khí -> Trúc Cơ -> Kim Đan...), Quy tắc phép thuật (Magic System).
*   [ ] **Full-Text Inject RAG:** Bất cứ khi nào Prompt có chứa từ khóa (Keyword) trùng với Lorebook, nội dung chi tiết sẽ được nhét ngay vào trí nhớ ngắn hạn của AI.

## 🖋️ 7. Phân Hệ Viết Lách & Chốt Chương (Text Editor) 
**Công nghệ:** Tip-tap Editor (hoặc Quill), API RESTful.

*   [ ] **Màn hình Editor Split-View:** Một nửa là đoạn Chat gợi ý với AI, Một nửa bên kia là Word Editor để chép chữ sang và mài giũa lại.
*   [ ] **Bấm Chốt Chương (Publish Chapter):** Đẩy kết quả cuối cùng sang `chapters` trong Postgres. Lúc này hệ thống tự động gọi Pipeline Background (Mục 4 và Mục 5) tái cấu trúc lại Graph và Vector Trí nhớ.

---
*(Danh sách này có thể mở rộng tùy vào độ khó và ý tưởng phát sinh trong quá trình xây dựng)*
