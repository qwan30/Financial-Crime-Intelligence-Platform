## 📌 Description
<!-- Tóm tắt ngắn gọn thay đổi này giải quyết vấn đề gì (Link issue / Task Brief nếu có) -->

## 💇‍♂️ Ponytail Review Checklist (BẮT BUỘC)
- [ ] Đã chạy `/ponytail-review` trước khi mở PR (Kết quả: **PASS**).
- [ ] **YAGNI**: Không có tham số, hàm helper hay abstraction thừa thãi.
- [ ] **Tái sử dụng**: Tận dụng tối đa code có sẵn trong repo và Standard Library.
- [ ] **Minimal Diffs**: Dạng mã nguồn ngắn gọn, dễ đọc, không over-engineering.

## 🧪 Verification & Test Evidence
<!-- Dẫn chứng cụ thể chứng minh code hoạt động đúng -->
- [ ] `uv run pytest -q` (Unit & Integration tests passed).
- [ ] `uv run ruff check .` & `uv run mypy src` (Green 100%).
- [ ] Test coverage tối thiểu >= 80%.

## 🛡️ Security & Invariants
- [ ] Không có hardcoded secrets / API keys.
- [ ] Schema input / boundary được validate chặt chẽ (Pydantic models).
- [ ] Không tự ý bịa mock/contract giả (*Anti-minted API*).
