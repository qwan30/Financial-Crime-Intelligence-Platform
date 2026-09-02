# Nhật Ký Quyết Định Kiến Trúc (Decision Log): AI Scientific Coding Loop

## Quyết Định 1: Tách Biệt Vòng Lặp Kép (Two-Timescale Feedback Architecture)
- **Vòng trong (Execution Feedback - Machine Loop):** Chạy nhanh, do Agent tự trị thực thi để thu hẹp khoảng cách từ mã nguồn tới mục tiêu đã niêm phong (`EpochContract`).
- **Vòng ngoài (Judgment Feedback - Human Loop):** Chạy chậm tại ranh giới Epoch, do Con người nắm giữ để quyết định mục tiêu có đúng đắn, có cần định hình lại (`REFRAME`) hay dừng (`ABORT`). Trạng thái `MACHINE_VERIFIED` không bao giờ đồng nghĩa với `PROJECT_ACCEPTED`.

## Quyết Định 2: Phân Tách Thẩm Quyền Phán Đoán (SLP Separation of Judgment)
- **Human:** Giữ Product Intent, Risk Envelope, Ngân sách và Quyết định cuối (Merge/Release/Irreversible Trade-offs).
- **Lead:** Đóng khung `EpochContract`, lập Council Brief trung lập, tổng hợp Dissent, và đưa ra `Project Acceptance Recommendation`. Tuyệt đối không tự code rồi tự nghiệm thu.
- **Peer:** Sở hữu Bounded Outcome trong Worktree được cấp quyền (Lease). Được quyền phản biện với các trạng thái `CONFIRM/CHALLENGE/REOPEN_REQUEST`.
- **Supervisor:** Giám sát quy trình, phát hiện anti-patterns (S1-S9), có quyền `PAUSE/ESCALATE` nhưng không can thiệp vào mã nguồn.

## Quyết Định 3: Lưu Trữ Bền Vững Trạng Thái & Tri Thức Thất Bại (Durable Artifacts & Negative Memory)
- Trạng thái dài hạn được lưu trữ trên đĩa (`Decision Log`, `Negative Memory Index`, `Worktree Leases`, `Candidate Manifests`), không phụ thuộc vào context chat.
- Ngăn chặn triệt để hiện tượng quên lỗi sau khi nén context (Compaction).

## Quyết Định 4: Rào Chắn Chống Goodhart Bằng Vector Gate Đa Chiều
- Không nén kết quả thành 1 điểm số duy nhất.
- Bắt buộc vượt qua 6 cổng trực giao: (1) Syntax/Type Gate, (2) Behavioral Contract Gate, (3) External Invariant Reconciliation, (4) Test-Integrity Gate, (5) Security/Resource Bounds, (6) Independent Reviewer trên Stable Candidate digest.
