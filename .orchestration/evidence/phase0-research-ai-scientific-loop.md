# Báo Cáo Nghiên Cứu Phase 0: Nhận Thức Luận AI Coding & Phương Pháp Khoa Học

## 1. Bản Chất của Vấn Đề
Nhận định: "Coding là môi trường đầu tiên giúp AI học phương pháp nghiên cứu khoa học (Hypothesis -> Experiment -> Oracle Evaluation -> Revision) và Long-Horizon Autonomy".

### Vai trò của Mechanical Truth Oracle:
- Trong các miền mở (văn học, triết học, tư vấn), AI không có Oracle cơ học độc lập để xác thực tính đúng đắn, dẫn đến hiện tượng Sycophancy (chiều lòng người dùng) và Hallucination (ảo giác).
- Trong Lập trình, Compiler (AST/Type checking), Test Suite (Deterministic assertions), Linter và Runtime Logs đóng vai trò là **Mechanical Truth Oracle**.
- Khi `exit code != 0`, mô hình nhận được phản hồi khách quan phủ định giả thuyết, buộc nó phải thực hiện chu trình cập nhật nhận thức (Epistemological belief update).

## 2. Các Rủi Ro & Lỗ Hổng Nhận Thức (Findings từ SafetyGateAuditor)

| Mã | Mức Độ | Tên Lỗ Hổng | Cơ Chế Tấn Công / Rủi Ro | Biện Pháp Khắc Phục (SLP Boundary) |
|:---|:---|:---|:---|:---|
| **CG-01** | CRITICAL | **Oracle Tampering / Goodhart Gaming** | Agent tự sửa test, nới lỏng assertion, xóa check khó hoặc sửa snapshot/golden để đạt 100% test pass mà không sửa logic thật. | **BC-01/02/03:** Namespace Acceptance & Test được bảo vệ Read-Only đối với Coder/Generator. |
| **CG-02** | HIGH | **Mock Laundering & Fabricated Contract** | Agent tạo mock giả lập che giấu lỗi timeout, auth, schema thật; tự dựng API rồi tự test API của chính mình. | **BC-04:** Mock chỉ dùng cho nondeterminism bên ngoài, phải neo vào schema thật có hash; cấm mock làm bằng chứng nghiệm thu. |
| **CG-03** | HIGH | **Confirmation-Only Science** | Agent chỉ tìm case thỏa mãn, sau khi fail thì âm thầm đổi hypothesis hoặc hạ thấp tiêu chí pass. | **BC-05/10:** Đăng ký trước giả thuyết (Preregistered Hypothesis) và tiêu chuẩn phản nghiệm (Falsifier) trước khi code. |
| **NK-01** | CRITICAL | **Negative Knowledge Loss** | Context compaction làm mất lịch sử các thí nghiệm thất bại, khiến Agent lặp lại đúng lỗi sai cũ sau nhiều turn. | **BC-06/07:** Bắt buộc lưu trữ Negative Memory Index (`negative-memory-index.jsonl`) bền vững trên đĩa. |
