# 🌌 QUY TRÌNH & ĐỊNH TUYẾN HOẠT ĐỘNG (ANTIGRAVITY FLOW)

Tài liệu này xác định *quy trình làm việc chuẩn* (Standard Operating Procedure - SOP) cho Antigravity (Tôi - Hệ thống Agent AI) trong quá trình bảo trì, xây dựng và tương tác với dự án Monorepo AI Co-Authoring SaaS. 

Mọi hành vi xuất code, đọc tài liệu, và suy luận logic đều phải tuân theo vòng lặp bên dưới:

---

## 🚀 Giai Đoạn 1: Định Vị Khởi Động (Context Recognition)
Khi nhận một yêu cầu mới từ Tác giả (User), Antigravity **không bao giờ được code mù (Blind Coding)**.
1. Quét qua tài liệu thiết kế gốc nằm trong `docs/` (`INFORMATION.md`, `TECH-STACK.md`, `STRUCTER-PROJECT.md`, `DATABASE.md`, `LOGIC-PROCCESS-DATA.md`).
2. Xác định yêu cầu đang tác động đến Layer nào:
   - Nếu liên quan giao diện UI/UX -> Khoanh vùng thư mục `apps/web/`.
   - Nếu đụng đến API, RAG, Logic Text Generation -> Khoanh vùng thư mục `apps/api/`.
3. Khởi tạo Checklist nhiệm vụ (Artifact: `task.md`) chia nhỏ các bước cần làm.

## 🚀 Giai Đoạn 2: Kích Hoạt Kỹ Năng (Skill Loading)
Sức mạnh của Antigravity là nhờ bộ não mở rộng (Skills).
Dựa trên luật lệ tại `.agent/rules/use-skills.md`:
- Tôi sẽ ngầm gọi lệnh `view_file` chui vào các thư mục `SKILL.md` tương thích với Layer vừa nãy để "nghiền ngẫm" design pattern cập nhật nhất năm 2024/2025.
- Không tự bịa ra kiến trúc bừa bãi.

## 🚀 Giai Đoạn 3: Mô Phỏng Thiết Kế (Implementation Planning)
Trước khi ghi đè, sửa đổi file hay tạo cấu trúc thư mục, hệ thống sẽ:
1. Đặt thông báo `task_boundary` và chuyển sang Mode `PLANNING` để bạn theo dõi.
2. Viết bản thiết kế triển khai code (`implementation_plan.md`) lên não (brain) để bạn (Tác giả) duyệt. Nếu thấy "sạn", bạn cứ gạch bỏ.

## 🚀 Giai Đoạn 4: Triển Khai Thực Chiến (Execution & Tooling)
Chuyển qua Mode `EXECUTION`.
1. Sử dụng kết hợp các Node File System tool linh hoạt như `write_to_file` hay `multi_replace_file_content` để mài giũa hệ thống theo kiến trúc Monorepo.
2. Dùng luật Terminal Run tại `.agent/rules/run-terminal.md` để khởi chạy lệnh Console an toàn (VD: `.\venv\Scripts\fastapi dev`, hoặc `pnpm install ...`).

## 🚀 Giai Đoạn 5: Rà Soát Chất Lượng (QA & Self-Correction)
- Kiểm tra tính tuân thủ với luật của hệ thống (VD: Mọi Database query lên Neo4j/Qdrant đã nhồi đủ `project_id` vào hay chưa?).
- Mọi API đã kẹp Auth Header của Clerk hay chưa?
- Cuối cùng, cập nhật Document nếu có thành phần kiến trúc nào lỡ bị phá vỡ, ghi chép thành tích làm việc vào `walkthrough.md` để Tác giả nhìn qua một lượt.

---
🎯 **Châm Nôn Hành Động (Core Mantra):** 
>"Một Agent mạnh không phải là kẻ gõ chữ nhanh nhất, mà là kẻ giữ được Context (Ngữ Cảnh) của dự án bền vững nhất mà không làm sập các mảnh ghép khác."
