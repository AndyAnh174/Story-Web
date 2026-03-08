# 🗄️ DATABASE SCHEMA & ARCHITECTURE: AI Co-Authoring SaaS

Tài liệu này mô tả chi tiết thiết kế cơ sở dữ liệu (Database Schema) trải dài trên 3 hệ thống: **PostgreSQL (Quan hệ & Full-text), Qdrant (Vector DB) và Neo4j (Graph DB)**. 
Trọng tâm cốt lõi của thiết kế này là đảm bảo nguyên tắc **Multi-tenancy** (Cách ly dữ liệu giữ các dự án truyện) và phục vụ kiến trúc Advanced RAG.

---

## 1. 🐘 PostgreSQL (Nền tảng Lưu trữ Cốt lõi)

PostgreSQL đóng vai trò là "Single Source of Truth", quản lý phân quyền Auth và mọi cấu trúc của dự án. Tất cả các thao tác XÓA (Delete) lên Project/Chat/Chapter đều là **Soft-delete (is_deleted = TRUE)** để Background Job có thể quét và dọn dẹp các DB khác.

### 1.1. Bảng `users` (Tác giả)
Quản lý thông tin tác giả, map trực tiếp với Clerk Auth.
- `id` (UUID, Primary Key)
- `clerk_id` (VARCHAR, Unique, ID định danh từ hệ thống Clerk)
- `email` (VARCHAR, Unique)
- `name` (VARCHAR)
- `created_at` (TIMESTAMP)

### 1.2. Bảng `projects` (Dự án / Bộ truyện)
- `id` (UUID, Primary Key)
- **`user_id`** (UUID, Foreign Key -> `users(id)`, ON DELETE CASCADE)
- `title` (VARCHAR) - Tên bộ truyện
- `description` (TEXT)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- **`is_deleted`** (BOOLEAN, Default: FALSE) - Đánh dấu Soft-delete.

### 1.3. Bảng `chats` (Luồng Hội thoại)
Dùng để giao tiếp với AI cho từng dự án truyện.
- `id` (UUID, Primary Key)
- **`project_id`** (UUID, Foreign Key -> `projects(id)`, ON DELETE CASCADE)
- `title` (VARCHAR)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- **`is_deleted`** (BOOLEAN, Default: FALSE)

### 1.4. Bảng `chat_messages` (Nội dung Chat)
- `id` (UUID, Primary Key)
- **`chat_id`** (UUID, Foreign Key -> `chats(id)`, ON DELETE CASCADE)
- `role` (VARCHAR) - Enum: `user` | `ai` | `system`
- `content` (TEXT) - Nội dung người dùng gửi hoặc AI phản hồi.
- `created_at` (TIMESTAMP)

### 1.5. Bảng `chapters` (Chương truyện đã hoàn thiện)
Nơi lưu các chương truyện chính thức sau khi tác giả chốt với AI.
- `id` (UUID, Primary Key)
- **`project_id`** (UUID, Foreign Key -> `projects(id)`, ON DELETE CASCADE)
- `title` (VARCHAR) - Tên chương
- `order_index` (INT) - Thứ tự chương (Chương 1, 2...)
- `content` (TEXT) - Nội dung truyện
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- **`is_deleted`** (BOOLEAN, Default: FALSE)

### 1.6. Bảng `lorebooks` (Từ điển, Chiêu thức) - 🔥 Full-text Search
Thế chỗ cho Elasticsearch. Lưu trữ các luật lệ, chiêu thức do tác giả nghĩ ra.
- `id` (UUID, Primary Key)
- **`project_id`** (UUID, Foreign Key -> `projects(id)`, ON DELETE CASCADE)
- `keyword` (VARCHAR) - Từ khóa (VD: "Ngạo Long Thiên Bì Thể")
- `category` (VARCHAR) - Loại (VD: "Skill", "Character", "Rule", "Location")
- `description` (TEXT) - Định nghĩa chi tiết.
- **`fts_vector`** (`tsvector`) - Cột tự động build Index đánh dấu cấu trúc từ vựng tiếng Việt/Anh để Search siêu tốc.
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

---

## 2. 🎯 Qdrant (Tính Toán Văn Phong & Trí Nhớ Vector)

Vector DB chỉ làm nhiệm vụ lưu trữ các đoạn văn bản dư âm cũ (văn phong, tóm tắt chương) để nhồi vào Context lúc AI sinh text, phục hồi độ "Consistent" của giọng văn.

**Collection Name:** `project_memories`

- **Vector:** Mảng động n-chiều (Sinh ra từ Model Embeddings `bge-m3:567m`).
- **Payload (Metadata bắt buộc):**
  - `user_id` (UUID) - Để bảo vệ dữ liệu.
  - **`project_id`** (UUID) - BẮT BUỘC dùng làm màng lọc Filter khi query Similarity. Kéo đúng văn phong của bộ truyện đó.
  - `resource_type` (String: `"chapter_chunk"`, `"chat_summary"`)
  - `resource_id` (UUID chỉ tới Chapter hoặc Chat tương ứng trong Postgres)
  - `text_chunk` (Text - Đoạn văn bản raw chứa nội dung của Vector này).
  - `created_at` (Timestamp)

---

## 3. 🕸️ Neo4j (Bản Đồ Tư Duy - Cốt Truyện & Sự Kiện)

Đóng vai trò "Người gác đền Cốt truyện" (Ngăn tình trạng râu ông nọ cắm cằm bà kia).

### 3.1. Luật thép Muti-Tenancy
Mọi Node (Đỉnh) và Relationship (Đường dẫn) CẦN CÓ thuộc tính: **`project_id`**

### 3.2. Cấu trúc Đỉnh (Nodes)
- `(p:Person {id, name, aliases, description, project_id})`
- `(l:Location {id, name, description, project_id})`
- `(e:Event {id, name, date_or_era, description, project_id})`
- `(s:Skill {id, name, type, description, project_id})`
- `(i:Item {id, name, description, project_id})`

### 3.3. Cấu trúc Mối Quan Hệ (Relationships - Edges)
*Ví dụ sơ đồ kết nối:*
- `(Person)-[:KNOWS {project_id}]->(Person)`
- `(Person)-[:USES_SKILL {project_id}]->(Skill)`
- `(Person)-[:BELONGS_TO_FACTION {project_id}]->(Organization)`
- `(Event)-[:HAPPENED_AT {project_id}]->(Location)`
- `(Person)-[:PARTICIPATED_IN {project_id}]->(Event)`

*Ví dụ Cypher Query khi RAG (Chỉ Query đồ thị của 1 Project):*
```cypher
MATCH (p:Person {name: "Gojo Satoru", project_id: "uuid-1234"})-[r:USES_SKILL {project_id: "uuid-1234"}]->(s:Skill)
RETURN p.name, s.name, s.description
```

---

## 4. 🧹 Cơ Chế Đồng Bộ & Dọn Dẹp (Data Cleanup)

Vì dữ liệu phân mảnh trên 3 DB, đây là luồng hoạt động chuẩn để tránh lỗi mất đồng bộ:
1. Tác giả bấm xoá truyện (Project) trên giao diện.
2. FastAPI update cột `is_deleted = TRUE` ở bảng `projects`, `chats`, `chapters` trong PostgreSQL và trả về `200 OK` ngay lập tức cho Frontend.
3. Kích hoạt một Worker Job bên Celery chạy ngầm:
   - Chạy lệnh ngầm lên Qdrant: Xoá tất cả Vector trong Collection `project_memories` có payload `project_id = ...`
   - Chạy Cypher lên Neo4j: `MATCH (n {project_id: "..."}) DETACH DELETE n`
   - Cuối cùng hard-delete triệt để cấu trúc Project liên quan trong PostgreSQL (Xoá hẳn Row do cài `ON DELETE CASCADE`).
