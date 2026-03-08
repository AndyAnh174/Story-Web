# 📖 PROJECT OVERVIEW: AI Co-Authoring SaaS Platform (LLMOps cho Tác giả)

## 1. Mô tả dự án
Đây là một Nền tảng SaaS (Software as a Service) chuyên biệt dành cho các nhà phát triển truyện, tác giả tiểu thuyết và manga. Nền tảng cung cấp một giao diện **Chat tương tác thông minh**, cho phép người dùng đóng vai trò là "Đạo diễn cốt truyện" cùng phối hợp với AI để sáng tác các tác phẩm dài kỳ (ví dụ: Ngoại truyện Jujutsu Kaisen, Thế giới Fantasy riêng...).
Hệ thống tích hợp xác thực người dùng (Auth) và kiến trúc **Advanced RAG (Vector + Graph + Full-text)** với cơ chế Multi-tenancy khắt khe, đảm bảo trí nhớ của AI chính xác, liên tục và dữ liệu của mỗi tác giả được bảo mật tuyệt đối.

## 2. Công nghệ (Tech Stack) & Kiến trúc Hạ tầng
Dự án được xây dựng theo chuẩn Microservices thu nhỏ/Monorepo, container hóa bằng Docker để dễ dàng scale trên các cụm máy chủ ảo (Debian/Proxmox).

### 2.1. Frontend & Quản lý mã nguồn (User & Workspace)
- **Framework:** Next.js (v16.1.6) App Router.
- **Kiến trúc:** Turborepo/Nx Monorepo.
- **Authentication (Auth):** Sử dụng **Clerk** để xử lý Đăng nhập (Google, Email), Quản lý phiên và Phân quyền trên Frontend. Backend FastAPI sẽ độc lập xác thực trực tiếp JWT token do Clerk cấp.
- **Giao diện:** Màn hình quản lý dự án truyện (Workspace) và Giao diện Chat tương tác thời gian thực (Real-time Chat UI) bằng Tailwind CSS.

### 2.2. Backend & Điều phối AI (The "Brain")
- **Framework:** FastAPI (Python) chuyên trị API bất đồng bộ và xử lý luồng stream (Server-Sent Events) cho UI Chat.
- **AI Framework:** Langchain điều phối Agent.
- **Hàng đợi (Queue):** Redis + Celery/RQ để quản lý các job gen text dài, chống timeout cho API.

### 2.3. AI Models & Endpoints
- **Embeddings (Tự host):** Model `bge-m3:567m` qua Ollama local tại `http://222.253.80.30:11434/api/embeddings` để tiết kiệm chi phí vector hóa văn bản hàng loạt của tác giả.
- **Sinh văn bản (Local LLM):** Model `gpt-oss:120b-cloud` qua API Ollama local tại `http://localhost:11434/` để tự chủ xử lý nội dung logic phức tạp.

### 2.4. Hệ thống Database Đa tầng (Multi-tenant Memory System)
Quy tắc sống còn: Mọi truy vấn phải đi kèm `user_id` và `project_id`.
- **PostgreSQL:** Lưu trữ cấu trúc cốt lõi (User, Project, Lịch sử Chat). Đặc biệt, sử dụng tính năng **Full-Text Search (tsvector)** tích hợp sẵn của Postgres để truy vấn chính xác tuyệt đối bộ thuật ngữ, chiêu thức đặc biệt (Lorebook) do tác giả định nghĩa (thay thế hoàn toàn Elasticsearch để giảm tải hệ thống).
- **Qdrant (Vector DB):** Phân tách không gian nhớ theo `payload = {user_id, project_id}`. Dùng để AI tìm lại văn phong và bối cảnh của các chương cũ.
- **Neo4j (GraphRAG):** Kiến trúc Knowledge Graph nhân vật/sự kiện. **Lưu ý Multi-tenancy:** BẮT BUỘC mọi Node (đỉnh) và Relationship (cạnh) khi lưu vào Neo4j đều phải gắn thêm thuộc tính `project_id`. Mọi truy vấn Cypher đều phải có điều kiện `WHERE n.project_id = "xyz"` để cách ly triệt để dữ liệu giữa các bộ truyện.

## 3. Luồng hoạt động cốt lõi (SaaS Chat Flow)
1. **Xác thực:** Tác giả đăng nhập qua Auth, chọn Dự án truyện (VD: Ngoại truyện JJK).
2. **Chat & Prompt:** Tác giả gửi yêu cầu (VD: "Viết cảnh Raito dùng Ngạo Long Thiên Bì Thể đỡ đòn").
3. **Retrieval (RAG):** FastAPI xác thực `user_id` + `project_id`, truy xuất PostgreSQL (lấy Lorebook chiêu thức), Qdrant (lấy bối cảnh) và Neo4j (lấy sơ đồ quan hệ) để xây dựng prompt hoàn chỉnh.
4. **Streaming Response:** LLM xử lý và FastAPI stream kết quả trả về giao diện Chat từng chữ một (như ChatGPT) để tối ưu trải nghiệm tác giả.
5. **Cập nhật Trí nhớ ngầm:** Sau khi chốt nội dung, hệ thống đẩy job vào Redis để tự động trích xuất thực thể mới vào Neo4j và vector hóa vào Qdrant.

## 4. Nguyên tắc Phát triển (Dành cho AI Assistant)
- Mã nguồn TypeScript/Python phải tuân thủ Typing nghiêm ngặt.
- BẮT BUỘC triển khai luồng Auth bảo mật từ Frontend xuống tận Backend API. Các endpoint FastAPI phải verify JWT token của Clerk lấy từ Header trước khi thao tác Database.
- Thiết kế Database schema trong PostgreSQL phải có khóa ngoại (Foreign Key) rõ ràng giữa User -> Projects -> Chats/Chapters...
- **Đồng bộ & Dọn dẹp dữ liệu (Data Cleanup):** Mọi thao tác XÓA bộ truyện hoặc XÓA hội thoại từ người dùng sẽ chỉ dán nhãn Soft-delete trong PostgreSQL để trả về API nhanh. Một Background Job (Celery) sẽ chịu trách nhiệm quét định kỳ và xóa vĩnh viễn (Hard-delete) các Node Neo4j và Vector Qdrant tương ứng để tránh rác hệ thống (Zombie Data).