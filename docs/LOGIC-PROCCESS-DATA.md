# 🧠 LOGIC PROCESS DATA: Xử lý Tình tiết & Trí nhớ AI

Tài liệu này định nghĩa luồng Logic xử lý dữ liệu phức tạp (Logic Process Data) khi AI tương tác với tác giả. Trọng tâm là giải quyết bài toán: **Làm sao để AI nhớ được một nhân vật vừa mới được tạo ra, một chiêu thức mới thi triển, hoặc "biết" rằng một nhân vật đã chết để không cho xuất hiện lại.**

Hệ thống hoạt động theo tôn chỉ: *Mỗi câu trả lời của AI không chỉ là text, mà còn là một Event biến đổi dữ liệu (Data Mutation Event) lên Graph & Vector.*

---

## 1. Vấn Đề (Pain Points) Trong Truyện Dài Kỳ
- Tác giả tự dưng chế ra một ông la sát tên "Kurama" chưa từng được định nghĩa.
- Tác giả cho "Kurama" dùng skill "Hắc Lôi".
- Tác giả cho nhân vật "Kento" bị nguyền rủa và **CHẾT**.
👉 Nếu chỉ dùng RAG Vector thông thường, AI sẽ quên Kurama ở chương sau, và có thể gọi hồn Kento sống dậy đi mua bánh mì.

---

## 2. Giải Pháp: AI Entity Extractor (Luồng Xử Lý Ngầm)

Sau **MỖI** lượt Chat mà tác giả bấm "Chốt" (Accept nội dung), FastAPI sẽ không chỉ lưu text vào Postgres mà còn đẩy một tác vụ qua Celery/Redis. Nhiệm vụ của Background Job này là gọi Model LLM (gpt-oss:120b-cloud) kích hoạt luồng **Entity Extractor (Trích xuất Thực thể)**.

### Buớc 2.1: LLM Phân Tích Sự Thay Đổi (Delta Analysis)
Job sẽ cấp cho AI toàn bộ 1 hoặc vài đoạn Chat vừa chốt, yêu cầu AI trả về một file **JSON strictly typed** (dùng Structured Output) mô tả những thứ vừa sinh ra hoặc thay đổi.

**Prompt Mẫu cho Extractor AI:**
```json
{
  "new_characters": [
    { "name": "Kurama", "description": "Lão quỷ la sát ẩn mình dưới vực." }
  ],
  "new_skills": [
    { "name": "Hắc Lôi", "used_by": "Kurama", "description": "Tia sét màu đen thiêu rụi linh hồn." }
  ],
  "character_status_changes": [
    { "name": "Kento", "old_status": "Alive", "new_status": "Dead", "reason_of_death": "Bị trúng Hắc Lôi của Kurama" }
  ],
  "new_events": [
    { "name": "Trận chiến dưới vực sâu", "participants": ["Kurama", "Kento"], "outcome": "Kento tử trận." }
  ]
}
```

### Bước 2.2: Cập Nhật Neo4j (Graph Mutation)
Khi nhận được output JSON trên, hệ thống Backend gõ lệnh Cypher vào Neo4j (Tất cả phải kẹp `project_id`):

1. **Sinh nhân vật mới:** `CREATE (p:Person {name: "Kurama", status: "Alive", project_id: "xyz"})`
2. **Sinh chiêu thức & Nối quan hệ:** 
   `MATCH (p:Person {name: "Kurama", project_id: "xyz"})`
   `CREATE (s:Skill {name: "Hắc Lôi", project_id: "xyz"})`
   `CREATE (p)-[:OWNS_SKILL {project_id: "xyz"}]->(s)`
3. **Cập nhật Trạng thái (CHẾT):** 
   `MATCH (p:Person {name: "Kento", project_id: "xyz"})`
   `SET p.status = "Dead", p.death_reason = "Bị trúng Hắc Lôi của Kurama"`

*(Ghi chú: Property `status` của Node Person cực kỳ quan trọng).*

---

## 3. Luồng Truy Xuất (Retrieval) Trước Khi AI Viết Tiếp

Khi tác giả gõ *"Viết tiếp cảnh ngày hôm sau ở học viện"*, AI phải được mớm đủ thông tin hiện tại.

### Bước 3.1: Full-Text Tìm Lorebook (Postgres)
Tìm các khái niệm tĩnh, chiêu thức gốc (Ví dụ: "Học viện là gì").

### Bước 3.2: Graph Traversal (Neo4j)
FastAPI sẽ truy xuất "Sơ đồ trạng thái" từ Neo4j để nhét vào System Prompt:
- Lấy danh sách các nhân vật đang xuất hiện ở `Location = "Học viện"`.
- Nhìn lướt qua xem có ai `status = "Dead"` không. Nếu có Kento => Ép thẳng vào System Prompt: `CẢNH BÁO: Nhân vật Kento đã (Dead) do "Bị trúng Hắc Lôi", tuyệt đối không cho xuất hiện hoặc nói chuyện.` 
- Load các kỹ năng của Kurama nếu hắn có tham gia cảnh này để AI biết hắn có "Hắc Lôi".

### Bước 3.3: Semantic Search Context (Qdrant)
Lấy 3 đoạn Vector gần nhất tóm tắt "Trận chiến dưới vực sâu" hôm qua để văn phong AI được liên tục.

---

## 4. System Prompt Chuẩn RAG Lõi
Đây là cách mọi thứ ráp lại để gửi sang Model sinh văn(`gpt-oss:120b-cloud`):

```text
[SYSTEM]
Bạn là một Đạo diễn Cốt truyện kỳ cựu. Bạn đang hỗ trợ tác giả viết tiếp tác phẩm (Project: {project_title}).

### 1. BỐI CẢNH HIỆN TẠI TỪ NE04J (Graph Memory)
- Kento: (STATUS: DEAD - Chết vì dính Hắc lôi). (CẤM CHO NHÂN VẬT NÀY SỐNG LẠI).
- Kurama: (STATUS: ALIVE - Có kỹ năng: Hắc Lôi).

### 2. THUẬT NGỮ (Lorebook)
- Hắc lôi: Tia sét đen...

### 3. TÓM TẮT CHƯƠNG TRƯỚC (Qdrant)
{qdrant_context_bge_m3}

### YÊU CẦU:
Hãy viết tiếp dựa trên yêu cầu của tác giả dưới đây. Tuân thủ tuyệt đối logic (Người chết không thể hành động).
```

---

## 5. Summary Flow
| Giai đoạn | Thao tác | Công nghệ Tương tác |
| :--- | :--- | :--- |
| **User Nhập Text** | `Retrieval` | Gọi Postgres (Lore) + Qdrant (Context) + Neo4j (Status/Entities). |
| **Gen Text** | `Inference` | Gửi System Prompt cho Local LLM `gpt-oss:120b`. |
| **User Chốt Story** | `Job Push` | Lưu PostgreSQL (Chats/Chapters). Pushed to Celery/Redis. |
| **Background Run** | `Extraction` | Dùng AI (hoặc Local LLM có function call) bóc xuất entities mới (JSON). |
| **Sync DB** | `Mutation` | Chạy lệnh Neo4j (Cập nhật sống/chết, skill mới) + Embed Qdrant văn bản mới. |

---

## 6. Cơ Chế Phối Hợp & Đồng Bộ Mảng Database (DB Coordination)

Để hệ thống hoạt động trơn tru không bị lỗi dữ liệu chéo, 3 Database (PostgreSQL, Qdrant, Neo4j) được phân công rõ rệt theo nguyên lý: **"Postgres làm chủ (Master), Qdrant và Neo4j làm thợ (Workers)".**

### 6.1. Nguyên lý Bất Biến (Source of Truth)

- **PostgreSQL là Source of Truth tuyệt đối:** Mọi thao tác tạo, sửa, xóa Project/Chapter/Chat của người dùng chỉ đụng trực tiếp vào Postgres đầu tiên.
- **Qdrant & Neo4j là "Views" phụ thuộc:** Chúng chỉ phản ánh lại trạng thái văn bản và logic từ Postgres. Không bao giờ có chuyện gọi trực tiếp API Xóa vào Neo4j từ phía Frontend.

### 6.2. Luồng Xóa Dữ Liệu An Toàn (Safe Deletion Flow)
Giả sử tác giả muốn xóa một đoạn đối thoại bị lỗi:

1. **Pha 1 (Lập tức):** Frontend gọi API Xóa. FastAPI cập nhật `is_deleted = TRUE` vào bảng `chat_messages` trong Postgres. Trả về `200 OK` cho Frontend phản hồi nhanh nhạy.
2. **Pha 2 (Background Job):** Celery nhận lệnh dọn dẹp. Job này sẽ tìm các ID tương ứng để xóa Vector trong Qdrant và xóa Node/Relationship trong Neo4j.
3. **Pha 3 (Transaction Rollback):** Nếu bước thao tác với Neo4j/Qdrant bị nghẽn mạng và **Thất bại (Fail)**, Worker Job sẽ báo lỗi đưa vào hàng chờ Dead-letter Queue để **thử lại (Retry)**, đảm bảo xóa rác đến cùng. Dù có Fail, AI lúc Get Data cũng không bị ảnh hưởng vì mọi Query RAG đều Join với bẳng Postgres kiểm tra `is_deleted = FALSE` làm tiền đề.

### 6.3. Giới hạn Trách Nhiệm (Responsibility Boundaries)
Sự kết hợp này là chìa khóa RAG thành công:

- Tại sao không gộp chung?
  - Muốn tìm chính xác từ khóa "Ngạo Long Thiên Bì Thể" => Postgres `tsvector` là trùm.
  - Muốn hỏi "Trong phòng có ai, người đó còn sống không?" => Neo4j Graph đi đường tắt nhanh nhất.
  - Muốn lấy 5 câu văn buồn bã nhất trận chiến hôm qua => Qdrant Search Vector lên ngôi.
👉 Việc Query song song cả 3 DB này trong lúc Retrieval (Bước 3) mất chưa tới 0.2s nhờ xử lý bất đồng bộ (Async) của FastAPI.

---

## 7. 🎭 Tối Hóa Mức Độ "Nhập Vai" Của AI (Hyper-Roleplaying & Alignment)

Mục tiêu lớn nhất là: **AI không được nói chuyện như một cái máy trợ lý (GPT), mà phải tư duy, hành văn và sáng tác y hệt bạn (Tác giả) hoặc một Co-Author đồng điệu.** RAG không chỉ để "nhớ sự kiện", RAG sinh ra để "thừa kế linh hồn" của bộ truyện.

### 7.1. Ep "Tone of Voice" (Văn phong) qua Qdrant
Khi tạo Vector Embedding cho Qdrant, không chỉ embed "Nội dung vắn tắt", mà phải **embed cả cách hành văn (Tone & Style)**. 
- Khi người dùng bấm "Chốt" đoạn văn, hệ thống sẽ đánh nhãn đoạn văn đó (Ví dụ: `Style: Bi tráng`, `Tone: Dark Fantasy`).
- Trong vòng lặp RAG, Prompt System ép LLM: *"Hãy phân tích nhịp điệu và từ vựng của 3 đoạn văn trong Qdrant này. BẮT BUỘC mô phỏng 100% giọng văn đó khi viết tiếp."*

### 7.2. System Prompt Chống "Xé Bản Cáo" (Out of Character - OOC)
Nhiều lúc AI LLM (nhất là các con OSS) sẽ bị ngáo và tự khuyên tác giả *"Bạo lực quá, thôi cho 2 bên làm hòa nhé"*. Để diệt tận gốc OOC:
- **Neo4j** sẽ cung cấp `Core Motivation` (Động lực cốt lõi) của Nhân vật để nhét vào Prompt. 
  *(Vd: Neo4j: Kurama - Động lực: Hủy diệt nhân loại. -> LLM bắt buộc chiều theo, tuyệt đối không cho hắn thiện lành lại).*
- Màng lọc an toàn (Safety Filter): TẮT hoặc SET ở mức thấp nhất trong config của `gpt-oss:120b` để nó dám viết các cảnh chiến đấu máu me, hắc ám (nếu truyện yêu cầu).

### 7.3. Luồng Tự Khắc Phục Lỗi Logic (Self-Correction Reflection)
Trước khi stream câu chữ đầu tiên ra màn hình Frontend, chạy ngầm 1 vòng lặp siêu tốc (<1s):
1. LLM nhá hàng bản draft.
2. Tool Code so bản draft này với đống luật trong **Postgres (Lorebook) + Neo4j**. (Ví dụ check xem nó có lỡ cho thằng Kento chết rồi mà thở lại không?).
3. Nếu vi phạm ranh giới hệ thống => Tự Reject và Gen lại trong tích tắc rồi mới đưa cho Tác giả xem. 
*(Đây chính là đỉnh cao của Advanced RAG: Tra cứu - Sinh văn - Sinh tự kiểm duyệt).*
