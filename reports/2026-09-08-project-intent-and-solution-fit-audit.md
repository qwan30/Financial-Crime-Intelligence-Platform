# Báo cáo Toàn diện: Phân tích Ý đồ Dự án, Độ phù hợp Giải pháp & Kiểm toán Bằng chứng Kỹ thuật (Project Intent & Solution-Fit Audit)

**Mã tài liệu:** `AUDIT-AML-INTENT-2026-01`  
**Ngày thực hiện:** 2026-09-08  
**Phạm vi Git Baseline:** `05f02c4e18165f7f6f4ff011351b1d8b089747fb..39fe39d619bb7f4d1eb8a391b5b2b4860380988c` (116 files, `+18,969/-94`)  
**Nhánh thượng nguồn (Upstream):** `origin/main` (đồng bộ tại `35ec354e2818f92a7298cb744ffe7f2af3327f5d`)  
**Kế hoạch đối chiếu:** `GIT_HISTORY_REVIEW_PLAN.md`  
**Phán quyết sẵn sàng (Readiness Verdict):** `WITH_FIXES` (Không sẵn sàng cho môi trường production nếu chưa xử lý các khiếm khuyết Critical & High)

---

## 1. Tóm tắt Điều hành & Bối cảnh Lịch sử Git (Executive Summary)

Báo cáo này là kết quả kiểm toán độc lập toàn diện theo kế hoạch `GIT_HISTORY_REVIEW_PLAN.md`, rà soát 116 tệp mã nguồn và tài liệu được tích hợp qua 9 PRs phụ thuộc lẫn nhau (CI, Evidence/Case, Agent, API, UI, Streaming, MLOps/Monitoring, Release Governance, Documentation).

### Đính chính Báo cáo Lịch sử Cũ:
Báo cáo trước đó ngày 02/09 (`reports/2026-09-02-pre-pr-review-summary.md`) ghi nhận số liệu `110 files, +15,583/-147`, tuyên bố *"100% Verified & Green, Production 100/100, 100% Coverage"*. Kiểm toán kỹ thuật xác nhận:
1. **Dữ liệu stale:** Báo cáo 02/09 được lập trước khi tách và tích hợp 9 PRs riêng lẻ; chưa phản ánh đúng cấu trúc commit first-parent hiện tại trên `main`.
2. **Tuyên bố độ phủ không có căn cứ:** Toàn bộ cấu hình CI (`.github/workflows/ci.yml`) và `pyproject.toml` hoàn toàn không có công cụ đo coverage (như `pytest-cov`). Số liệu 100% coverage là tự khai và chưa từng được đo lường thực tế.
3. **Báo xanh giả lập (False Confidence):** 572/572 tests đều pass, nhưng các assertions chủ yếu kiểm tra tính tự khớp cú pháp của mã nguồn (tautological) hoặc chạy trên mock 100% lưu lượng mạng, che giấu các khiếm khuyết nghiêm trọng về vật lý thời gian, khả năng lưu trữ và tích hợp API.

---

## 2. Bảng Đối chiếu Độ Phù Hợp: Bài toán — Đầu vào — Giải pháp — Phán quyết

Tiêu chuẩn đánh giá: **Nghiên cứu thực chứng địa phương (Local-first Empirical Research)**. Trạng thái code chạy được hoặc pass unit test không tự động cấu thành phán quyết `FIT`.

| Bài toán AML (`problem_id`) | Đầu vào & Giả định thực tế | Giải pháp đã triển khai | Phán quyết | Bằng chứng thực nghiệm & Giới hạn | Đề xuất cốt lõi |
|---|---|---|---|---|---|
| **PROB-DATA-INTAKE**<br>Nạp dữ liệu & kiểm soát đĩa | **Input:** AMLSim 20K synthetic ticks, đĩa local <8GB.<br>**Giả định:** Relative tick dùng làm thời gian; nhãn `nodes.csv.isFraud` là account-level, KHÔNG có ground truth đường đi. | `SOL-DATA-01`:<br>Capacity preflight, reason-coded quarantine, source label isolation (`src/fincrime/data/`). | **FIT_WITH_LIMITS** | **Probe 1 & Hash:** Kiểm soát dung lượng headroom chặn download quá tải thành công.<br>**Giới hạn:** Chỉ dùng cho smoke test nạp và trích xuất feature; không thể dùng đánh giá thuật toán trace. | Duy trì kiến trúc nạp an toàn; mở rộng sang dữ liệu Napas/banking thật khi có thỏa thuận. |
| **PROB-DETECTION-ALERT**<br>Baseline luật cảnh báo | **Input:** Giao dịch sổ cái tài khoản, ngưỡng FATF/SBV.<br>**Giả định:** Mẫu rửa tiền cơ bản tuân theo luật cố định; sinh nhiều cảnh báo giả. | `SOL-DET-01`:<br>Deterministic AML heuristics & graph features (`src/fincrime/features/`, `baselines.py`). | **FIT** | In/out degree, flow sums point-in-time chính xác.<br>**Miền hợp lệ:** Lớp baseline bắt buộc tuân thủ. | Giữ nguyên làm nền tảng unskippable; luôn đo metric của luật bên cạnh ML. |
| **PROB-DETECTION-ALERT**<br>Triage trong ngân sách K=100 | **Input:** Vector đặc trưng tài khoản, nhãn `isFraud`.<br>**Giả định:** LightGBM cải thiện Precision@K so với luật trong K=100 (`configs/research/baseline.json`). | `SOL-DET-02`:<br>LightGBM baseline & ma trận K=100 (`src/fincrime/training/baselines.py`). | **FIT_WITH_LIMITS** | Mã nguồn huấn luyện hoàn chỉnh. Tuy nhiên thư mục `research/reports/` rỗng, `baseline.json` chứa hash giả (`aaa...`), chưa có checkpoint đối chứng PR-AUC thực. | Chạy thực nghiệm hoàn chỉnh trên dữ liệu chuẩn hóa, lưu trữ artifact đối chứng. |
| **PROB-DETECTION-ALERT**<br>Học biểu diễn đồ thị (GNN) | **Input:** Đồ thị NetworkX, đặc trưng nút.<br>**Giả định:** GraphSAGE đem lại lift vượt trội so với LightGBM; GraphSAGE bắt buộc cho research release (`README.md:26`). | `SOL-DET-03`:<br>PyG 2-layer GraphSAGE module & NeighborLoader (`src/fincrime/training/graph.py`). | **INSUFFICIENT_EVIDENCE** | Có mã PyG nhưng không có checkpoint đã fit, không có báo cáo chứng minh cải thiện so với LightGBM. Chi phí tính toán local cao. | Hạ cấp GraphSAGE thành track nghiên cứu thứ cấp; không làm điều kiện tiên quyết cho V1. |
| **PROB-TRACING-PATH**<br>Truy vết dòng tiền đa bước | **Input:** Đồ thị giao dịch có hướng, cutoff thời gian.<br>**Giả định:** Giao dịch lớn đại diện cho rửa tiền; thuật toán tham lam tìm được đường tiền liên quan; 4 hops / 100 edges là đủ. | `SOL-TRACE-01`:<br>Thuật toán mở rộng đồ thị tham lam theo số tiền lớn `generate_candidates` (`src/fincrime/tracing/candidates.py`). | **MISFIT** | **Probe 8:**<br>1) Vi phạm nhân quả thời gian: Tiền rời tài khoản lúc 09:00 vẫn nối tiếp sau tiền đến lúc 10:00 (chảy lùi về quá khứ).<br>2) Bỏ sót smurfing: Ưu tiên amount lớn khiến đường dây chia nhỏ recall = 0%, nhiễm bẩn 100%. | **Bắt buộc viết lại thuật toán:** Ràng buộc `t_out >= t_in`; phân bổ ngân sách cạnh theo nhánh thay vì tham lam amount. |
| **PROB-TRACING-PATH**<br>Xếp hạng đường đi nghi vấn | **Input:** Tập đường đi ứng viên từ trace engine.<br>**Giả định:** Có nhãn gold độc lập cho từng cạnh/đường đi để huấn luyện LambdaRank. | `SOL-TRACE-02`:<br>LightGBM LambdaRank và heuristic ranker (`src/fincrime/tracing/rankers.py`). | **INSUFFICIENT_EVIDENCE** | Code LambdaRank chuẩn hóa và hàm loại trừ UNKNOWN hoạt động; tuy nhiên repo hoàn toàn không có ground truth đường đi độc lập (TraceBench rỗng). | Tạo hoặc thu thập benchmark có nhãn đường đi trước khi công bố hiệu quả ranking. |
| **PROB-EXPLAIN-CASE**<br>Toàn vẹn chuỗi chứng cứ | **Input:** Metadata case, danh sách evidence ID, snapshot time.<br>**Giả định:** Băm SHA-256 bảo đảm tính toàn vẹn; lưu trữ bộ nhớ RAM đáp ứng được nhu cầu local. | `SOL-EXP-01`:<br>EvidenceItem và CaseSnapshot tính băm SHA-256 (`src/fincrime/cases/`, `evidence/`). | **FIT_WITH_LIMITS** | **Probe 4:** Băm SHA-256 phát hiện chính xác mọi sửa đổi đơn byte.<br>**Khiếm khuyết (Finding 4):** Lưu trữ 100% trên RAM; toàn bộ vụ án bốc hơi khi restart server. | Bổ sung engine lưu trữ SQLite nhẹ dùng chung interface hiện tại. |
| **PROB-EXPLAIN-CASE**<br>Trực quan hóa mạng lưới điều tra | **Input:** Payload tổng hợp WorkbenchData qua HTTP.<br>**Giả định:** Web UI kết nối thông suốt với backend để hiển thị đồ thị và bằng chứng. | `SOL-EXP-02`:<br>React 19 + Vite + Cytoscape Workbench (`apps/investigator-web/`). | **FIT_WITH_LIMITS** | **Probe 5:** Giao diện hiển thị tốt mock data. Tuy nhiên `api.ts` để `API_BASE = ""` và Vite dev thiếu reverse proxy, lỗi 404 khi gọi backend thật. Playwright pass nhờ mock 100% mạng. | Thêm cấu hình proxy trong `vite.config.ts` trỏ `/cases` sang `127.0.0.1:8000`. |
| **PROB-AGENT-HYPOTHESIS**<br>AI Copilot lập giả thuyết vụ án | **Input:** CaseSnapshot, Evidence summaries, prompt.<br>**Giả định:** Citation validation bảo đảm AI không bịa đặt; LLM_OFF cho phép ứng dụng hoạt động ngoại tuyến. | `SOL-AGENT-01/02`:<br>GuardedDeepSeekProvider, BudgetController & kiểm tra citation ID (`src/fincrime/agent/`). | **FIT_WITH_LIMITS** | **Probe 6:** LLM_OFF hoạt động tốt (trả về `AI_UNAVAILABLE`). Tuy nhiên citation guard chỉ kiểm tra set membership: AI bịa đặt số tiền 1 tỷ VND nhưng gắn citation thật (100 VND) vẫn qua! `GET /workbench` gọi lại LLM tốn phí. | Thêm cache kết quả giả thuyết theo `snapshot_hash`. Kiểm tra ràng buộc ngữ nghĩa số tiền. |
| **PROB-HUMAN-FEEDBACK**<br>Thu nhận quyết định điều tra viên | **Input:** Quyết định đóng case (SAR, False Positive, Monitor), lý do, snapshot_hash.<br>**Giả định:** Feedback gắn với snapshot vụ án và đưa vào pipeline cải thiện mô hình. | `SOL-FEEDBACK-01`:<br>AnalystFeedbackEvent và route `POST /cases/{id}/feedback` (`src/fincrime/cases/service.py`). | **MISFIT** | **Probe 4:** Không có pipeline nối feedback về model. API chấp nhận `snapshot_hash` tùy ý từ client mà không đối chiếu với case snapshot! Dữ liệu nằm trên RAM. | Bắt buộc kiểm tra `req.snapshot_hash == cs.snapshot_hash`. Lưu feedback xuống đĩa/DB. |
| **PROB-REPLAY-RELEASE**<br>Tương đương luồng & batch | **Input:** Luồng TransactionEvent có thứ tự thời gian.<br>**Giả định:** Bộ tích lũy đồ thị online trùng khớp hoàn toàn với hàm batch offline tại cùng cutoff. | `SOL-REPLAY-01`:<br>OnlineGraphAccumulator và compute_offline_features (`src/fincrime/streaming/`). | **FIT** | **Probe 1:** Đạt mức bit-exact (`.hex()` giống nhau tuyệt đối) với in/out degree và flow sums. Cách ly bản ghi lỗi JSONL tốt. | Giữ nguyên harness kiểm chứng này; mở rộng sang model scoring parity. |
| **PROB-REPLAY-RELEASE**<br>Niêm phong gói phát hành | **Input:** Danh mục tệp artifact trên đĩa, chỉ số PSI, cờ test pass.<br>**Giả định:** Release manifest chứng minh phần mềm đã vượt qua test suite và kiểm toán drift. | `SOL-REPLAY-03`:<br>build_release_manifest & verify_release_manifest (`src/fincrime/release/manifest.py`). | **FIT_WITH_LIMITS** | **Probe 7:** Xác thực mã băm SHA-256 các tệp trên đĩa nghiêm ngặt.<br>**Giới hạn:** Cờ `tests_passed` là tham số boolean tự truyền vào, không kiểm tra kết quả pytest thực tế. | Ràng buộc lệnh build manifest với việc đọc và kiểm tra tệp `pytest.xml` tự động. |

---

## 3. Danh mục & Đánh giá Chi tiết 17 Tuyên bố Kỹ thuật (Claims & Evidence)

Toàn bộ 17 tuyên bố kỹ thuật được trích xuất từ các tài liệu đặc tả, mã nguồn và kế hoạch tích hợp đã được thẩm tra độc lập:

| Mã Claim | Tuyên bố Kỹ thuật (Technical Claim) | Thẩm quyền & Căn cứ (Authority) | Trạng thái Audit | Bằng chứng Thực nghiệm & Giới hạn |
|---|---|---|---|---|
| **CLAIM-001** | Kiểm tra dung lượng đĩa trước khi tải/giải nén để chống cạn kiệt đĩa máy local. | `specs/2026-08-31-...design.md:25`, `src/fincrime/feasibility/resources.py` | **VERIFIED_RUNTIME** | Probe xác nhận dung lượng headroom được kiểm tra trước khi ghi file; từ chối an toàn khi thiếu đĩa. |
| **CLAIM-002** | Giao dịch sai định dạng, vô hạn hoặc số tiền âm được cách ly vào file JSONL kèm mã lý do. | `specs/2026-08-31-...design.md:35`, `src/fincrime/data/quarantine.py` | **VERIFIED_RUNTIME** | Quarantine store ghi nhận chính xác bản ghi lỗi và lý do, không làm rơi rớt dữ liệu âm thầm. |
| **CLAIM-003** | Nhãn `nodes.csv.isFraud` trong AMLSim là account-level, tuyệt đối không dùng làm feature hoặc ground truth đường đi. | `specs/2026-08-31-...design.md:38`, `src/fincrime/data/manifest.py` | **VERIFIED_RUNTIME** | Khởi tạo manifest cô lập nhãn hoàn toàn khỏi pipeline trích xuất đặc trưng và đồ thị. |
| **CLAIM-004** | Luật heuristic xác định cung cấp cảnh báo baseline minh bạch, không thể bỏ qua cho tuân thủ AML. | `specs/reviews/2026-08-29-...md:18`, `src/fincrime/features/account.py` | **SOURCE_ONLY** | Code và unit test có đầy đủ; chưa có báo cáo chạy thực tế trên tập dữ liệu ngân hàng thật. |
| **CLAIM-005** | Mô hình LightGBM vượt trội so với luật xác định về Precision@K trong ngân sách K=100. | `configs/research/baseline.json:3,8-10`, `src/fincrime/training/baselines.py` | **CONTRADICTED** | Giả thuyết được đăng ký trước nhưng repo rỗng thư mục artifact model; `baseline.json` chứa hash giả (`aaa...`). |
| **CLAIM-006** | GraphSAGE là thành phần bắt buộc phải có cho đợt phát hành nghiên cứu. | `docs/architecture/README.md:26` | **CONTRADICTED** | Xung đột trực tiếp với tài liệu ngày 29/08; mã nguồn PyG có sẵn nhưng không có checkpoint đã fit hay bằng chứng nâng cao hiệu quả. |
| **CLAIM-007** | Thuật toán Deep Trace sinh ra các đường đi có hướng nhất quán và tuân thủ thứ tự thời gian. | `plans/2026-08-30-...tracing.md:1490`, `src/fincrime/tracing/candidates.py` | **CONTRADICTED** | `generate_candidates` chỉ lọc `timestamp <= cutoff` tĩnh, không kiểm tra `t_out >= t_in`. Cho phép tiền chảy lùi thời gian. |
| **CLAIM-008** | Sắp xếp tham lam theo số tiền lớn giúp phát hiện đáng tin cậy các đường dây rửa tiền. | `src/fincrime/tracing/candidates.py:45-65` | **CONTRADICTED** | Dưới ngân sách cạnh hữu hạn, sắp xếp theo amount lớn bỏ sót 100% các nhánh chia nhỏ (smurfing), recall = 0%. |
| **CLAIM-009** | Băm SHA-256 bảo đảm tính bất biến mật mã của bằng chứng và snapshot vụ án. | `specs/reviews/2026-08-29-...md:21`, `src/fincrime/cases/evidence.py` | **VERIFIED_RUNTIME** | Tính toán băm SHA-256 chuẩn hóa, phát hiện chính xác mọi thay đổi 1 byte trong payload bằng chứng. |
| **CLAIM-010** | Bằng chứng và snapshot vụ án được lưu trữ bền vững cho điều tra viên và thanh tra. | `docs/architecture/README.md:33`, `src/fincrime/cases/service.py` | **CONTRADICTED** | Dữ liệu lưu trong RAM (`dict`). Khởi động lại server hoặc worker fork làm mất 100% hồ sơ vụ án. |
| **CLAIM-011** | Giao diện React Workbench kết nối thông suốt với Case API backend để xử lý vụ án. | `plans/2026-08-30-investigator-deepseek.md`, `apps/investigator-web/` | **MOCK_ONLY** | Playwright test mock 100% qua `page.route()`. Runtime thật bị lỗi 404 do `vite.config.ts` thiếu proxy tới port 8000. |
| **CLAIM-012** | Kiểm tra trích dẫn bắt buộc bảo đảm suy luận AI có căn cứ thực tế từ bằng chứng vụ án. | `src/fincrime/agent/guard.py:25-80` | **CONTRADICTED** | Guard chỉ kiểm tra ID membership trong snapshot; không kiểm tra nội dung số tiền. AI có thể bịa đặt số tiền tùy ý. |
| **CLAIM-013** | Nền tảng tự động hạ cấp an toàn sang `AI_UNAVAILABLE` khi không có API key LLM. | `specs/reviews/2026-08-29-...md:29`, `src/fincrime/agent/provider.py` | **VERIFIED_RUNTIME** | Xử lý lỗi không có key mượt mà, trả về envelope chuẩn, giao diện vẫn hiển thị bằng chứng và đồ thị bình thường. |
| **CLAIM-014** | Phản hồi đóng vụ án của điều tra viên được thu nhận và tích hợp vào pipeline cải tiến mô hình. | `docs/architecture/README.md:15`, `src/fincrime/cases/service.py` | **CONTRADICTED** | Feedback lưu trong RAM `_feedback`, không có API đọc lại công khai và không có pipeline nối dữ liệu về model. |
| **CLAIM-015** | Bộ tích lũy đồ thị online khớp từng bit (`.hex()` giống nhau) với hàm tính batch offline. | `src/fincrime/streaming/state.py`, `tests/streaming/test_scoring_parity.py` | **VERIFIED_RUNTIME** | Độ tương đương số học đạt mức bit-exact tuyệt đối đối với in/out degree và flow sums tại cutoff thời gian. |
| **CLAIM-016** | Release manifest chứng minh bằng mật mã rằng test suite đã pass trước khi niêm phong. | `src/fincrime/release/manifest.py:15-60` | **CONTRADICTED** | `build_release_manifest` nhận `tests_passed: bool` như tham số do người gọi tự truyền, không kiểm tra receipts pytest. |
| **CLAIM-017** | Tập corpus gold benchmark nạp đầy đủ đồ thị đa bước và đánh giá suy luận AI trên đồ thị. | `data/manifests/eval_corpus_gold_cases.json`, `src/fincrime/agent/evaluation.py` | **CONTRADICTED** | Lệch khóa giữa manifest (`graphEdges`) và loader (`trace.edges`) khiến đồ thị nạp vào có đúng 0 nodes và 0 edges. |

**Tổng hợp trạng thái 17 Claims:**
- **VERIFIED_RUNTIME:** 6 claims (35.3%)
- **SOURCE_ONLY:** 1 claim (5.9%)
- **MOCK_ONLY:** 1 claim (5.9%)
- **CONTRADICTED:** 9 claims (52.9%)

---

## 4. Kết quả Thực chứng từ 8 Probes Độc lập (Runtime Evidence)

Tất cả các kết quả dưới đây được ghi nhận qua kịch bản kiểm thử độc lập không phụ thuộc vào bộ test nội bộ:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           KẾT QUẢ 8 PROBES ĐỘC LẬP (EVIDENCE SUMMARY)                          │
├──────────┬─────────────────────────────────────┬───────────────────┬───────────────────────────┤
│ Probe ID │ Tên kịch bản & Mục tiêu kiểm chứng  │ Trạng thái thực tế│ Phán quyết kỹ thuật       │
├──────────┼─────────────────────────────────────┼───────────────────┼───────────────────────────┤
│ PROBE-01 │ Point-in-time scoring parity        │ Passed (Hex exact)│ VERIFIED_BIT_EXACT        │
│ PROBE-02 │ Training truth & State progression  │ Bypassed gate     │ NO_EXECUTION_GATE         │
│ PROBE-03 │ Corpus hydration & Conflict swallow │ 0 nodes/edges     │ SCHEMA_KEY_MISMATCH       │
│ PROBE-04 │ Case API & Feedback hash validation │ Hash mismatch OK  │ SNAPSHOT_HASH_BYPASS      │
│ PROBE-05 │ UI out-of-the-box backend connect   │ Failed (404/cors) │ INTEGRATION_PROXY_GAP     │
│ PROBE-06 │ Citation validation & GET idempotency│ Fake claims passed│ MEMBERSHIP_ONLY_NO_TRUTH  │
│ PROBE-07 │ Release manifest & Test verification│ Tamper detected   │ CALLER_DECLARED_BOOLEAN   │
│ PROBE-08 │ Temporal causality & Smurfing recall│ Time jump / 0% rec│ CAUSALITY_VIOLATION_FLAW  │
└──────────┴─────────────────────────────────────┴───────────────────┴───────────────────────────┘
```

### Quan sát chi tiết từng Probe:
1. **Probe 1 (Point-in-time Parity):** Giao dịch trước cutoff $T=10:15$ được tích lũy online và so sánh với oracle tính batch offline. Từng trường số thực (`in_degree`, `out_degree`, `incoming_amount`, `outgoing_amount`) so sánh bằng `.hex()` đều trùng khớp 100%. Giao dịch trùng lặp ID bị từ chối; giao dịch sau cutoff không làm sai lệch giá trị.
2. **Probe 2 (Training State Progression):** Khởi tạo `TrainingRunState(PREREGISTERED)`, gọi tuần tự `advance()` qua các bước. Trạng thái đạt `DECIDED` thành công mà không cần nạp dữ liệu, không cần huấn luyện mô hình, và không cần tính bất kỳ metric nào.
3. **Probe 3 (Corpus Hydration & Error Swallowing):** Nạp `eval_corpus_gold_cases.json` vào `InMemoryGraphRepository` qua hàm `populate_corpus_fixtures`. Do manifest dùng trường `graphEdges` và `traceEdgeIds` trong khi hàm nạp đọc `trace.nodes` và `trace.edges`, đồ thị được nạp có chính xác **0 nodes và 0 edges**. Ngoài ra, khi preseed một bằng chứng trùng ID nhưng khác payload, hàm nuốt chửng ngoại lệ `EvidenceConflict`.
4. **Probe 4 (Case API & Feedback Hash):** API trên FastAPI TestClient hoạt động tốt ở chế độ `deepseek_provider = None` (trả về `AI_UNAVAILABLE`). Tuy nhiên, khi gửi feedback với `snapshot_hash = "ffffffff..."` giả mạo không khớp với hash của case, API vẫn trả về HTTP 200 và lưu hash giả vào `_feedback`.
5. **Probe 5 (UI Connection):** `apps/investigator-web/src/api.ts` để `API_BASE = ""` và `vite.config.ts` không cấu hình proxy. Mở đồng thời Vite dev (cổng 5173) và FastAPI (cổng 8000), trình duyệt gửi request tới `http://127.0.0.1:5173/cases/case_001/workbench` và nhận lỗi 404 từ Vite dev server.
6. **Probe 6 (LLM Citation & Idempotency):** Cung cấp bằng chứng *"Số tiền chuyển là 100 VND"*. Giả lập LLM trả về claim bịa đặt *"Chuyển 1,000,000,000 VND cho tổ chức tội phạm"* kèm citation ID thật `ev-01`. Guard kiểm tra thấy ID tồn tại nên cho qua toàn bộ kết quả. Đồng thời, gọi `GET /workbench` hai lần kích hoạt gọi API LLM cả hai lần (không có cache).
7. **Probe 7 (Release Manifest):** Sửa đổi 1 byte trong file artifact làm `verify_release_manifest` phát hiện và từ chối ngay. Tuy nhiên, manifest chấp nhận cờ `tests_passed: bool` trực tiếp từ caller mà không kiểm tra log hay file kết quả test.
8. **Probe 8 (Temporal Causality & Smurfing Recall):**
   - *Kịch bản nghịch đảo thời gian:* Giao dịch A $\rightarrow$ B 100 VND lúc 10:00 và B $\rightarrow$ C 90 VND lúc 09:00. `generate_candidates` trả về cả hai cạnh nối tiếp, cho phép tiền chuyển đi trước khi được nhận.
   - *Kịch bản smurfing:* Nhánh lành tính lớn A $\rightarrow$ B 10,000 VND và nhánh chia nhỏ A $\rightarrow$ D 100 VND $\rightarrow$ E 90 VND. Dưới ngân sách `max_edges=2`, thuật toán tham lam chọn toàn bộ nhánh 10,000 VND, đạt **recall = 0%** trên dòng tiền chia nhỏ và **nhiễm bẩn 100%**.

---

## 5. Kiểm toán Test Suite & Cơ chế "Tự tin Sai lệch" (False Confidence)

Hệ thống có **552 unit tests Python**, **18 unit tests Frontend** và **2 Playwright E2E tests**, tất cả đều báo xanh (100% pass rate). Tuy nhiên, phân loại 572 tests vào 3 tầng bảo vệ cho thấy:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PHÂN BỔ 3 TẦNG BẢO VỆ CỦA BỘ TEST SUITE                         │
├─────────────────────────────────────────┬────────────┬────────────┬────────────────────┤
│ Tầng bảo vệ kiểm thử (Testing Tier)     │ Số lượng   │ Tỉ lệ %    │ Bản chất bảo vệ    │
├─────────────────────────────────────────┼────────────┼────────────┼────────────────────┤
│ Tầng 1: Đúng Implementation (Cú pháp)   │ 368 tests  │ 64.3%      │ Code chạy tự khớp  │
│ Tầng 2: Đúng Đặc tính Miền (Invariance) │ 184 tests  │ 32.2%      │ Băm SHA, Parity hex│
│ Tầng 3: Hữu ích trên Dữ liệu Đại diện   │ 20 tests   │ 3.5%       │ Chưa có dữ liệu thật│
├─────────────────────────────────────────┴────────────┴────────────┴────────────────────┤
│ Tổng cộng kiểm thử tự động              │ 572 tests  │ 100.0%     │ Độ phủ: CHƯA ĐO    │
└─────────────────────────────────────────┴────────────┴────────────┴────────────────────┘
```

### Nguyên nhân sinh ra False Confidence:
1. **Thuật toán vi phạm nhân quả nhưng test vẫn pass:** `test_candidates.py` chỉ assert số lượng cạnh $\le max\_edges$ và cạnh sắp xếp giảm dần theo amount. Vì test chỉ assert lại đúng hành vi mà code đang làm, nên một thuật toán cho phép tiền đi lùi thời gian vẫn pass 100%.
2. **Nạp đồ thị 0 cạnh nhưng evaluation test vẫn pass:** `test_evaluation.py` nạp corpus bị lệch tên trường khiến đồ thị rỗng. Tuy nhiên test chỉ assert `result.case_count == 10` mà không kiểm tra độ sâu đồ thị hay chất lượng trích dẫn.
3. **Mock 100% mạng che giấu lỗi tích hợp:** Playwright `workbench.spec.ts` dùng `page.route()` chặn toàn bộ request đến `/cases/**`. E2E test pass hoàn hảo trong khi ứng dụng thật không thể gọi backend do thiếu proxy.

---

## 6. Tổng hợp Hội đồng Phản biện (Council Debate Synthesis)

Hội đồng 4 tiếng nói độc lập đã được triệu tập để đánh giá các mâu thuẫn:

- **Architect (Kiến trúc sư):** Hệ thống có kỷ luật mật mã rất tốt ở từng module riêng lẻ (băm SHA-256, bit-exact parity), nhưng bị đứt gãy kết nối giữa các tầng. Ưu tiên hàng đầu là sửa nhân quả thời gian và lưu trữ SQLite.
- **Skeptic (Người hoài nghi):** Dự án đang giải bài toán AML tưởng tượng. Toàn bộ tầng GNN và LLM tạo ảo giác thông minh nhưng làm việc kém hơn một câu lệnh SQL 5 dòng có điều kiện `out_time >= in_time`. Đề xuất: Cắt bỏ GNN và LLM, chỉ dùng luật và SQL.
- **Pragmatist (Người thực dụng):** Bỏ qua GNN không làm mất tính năng thực tế nào vì chưa có model nào được fit. Chỉ cần 3 dòng proxy Vite, SQLite và sửa điều kiện `t_out` là cứu được 90% giá trị sản phẩm local.
- **Critic (Nhà phê bình):** Cảnh báo rủi ro pháp lý: AI bịa đặt số tiền nhưng vẫn pass citation guard; dữ liệu xóa sạch sau khi restart vi phạm chuỗi chứng cứ (chain-of-custody).

### Phán quyết Đồng thuận:
Giữ lại LightGBM như mô hình xếp hạng phụ trợ và LLM như trợ lý tóm tắt có kiểm soát chặt chẽ; loại bỏ GraphSAGE/HGT khỏi điều kiện hoàn thành V1; tập trung toàn lực sửa thuật toán truy vết và bền vững hóa dữ liệu.

---

## 7. Danh mục 9 Phát hiện Kỹ thuật (Severity-Ranked Findings)

1. **FINDING-001 (CRITICAL):** Thuật toán `generate_candidates` vi phạm nhân quả thời gian, cho phép tiền chuyển đi trước khi chuyển đến (`src/fincrime/tracing/candidates.py:48-70`).
2. **FINDING-002 (CRITICAL):** Heuristic sắp xếp tham lam theo số tiền lớn loại bỏ hoàn toàn các đường dây smurfing (recall = 0%) dưới ngân sách cạnh (`src/fincrime/tracing/candidates.py:49,68`).
3. **FINDING-003 (CRITICAL):** Lệch tên trường giữa manifest và hàm nạp khiến đồ thị đánh giá frozen gold benchmark có 0 nodes và 0 edges, nuốt chửng ngoại lệ xung đột (`src/fincrime/agent/evaluation.py:172,196-199`).
4. **FINDING-004 (HIGH):** Toàn bộ kho lưu trữ CaseService, EvidenceStore và Feedback được viết bằng `dict` trên RAM, làm bốc hơi dữ liệu khi restart server (`src/fincrime/cases/service.py:25-35`).
5. **FINDING-005 (HIGH):** Route `POST /cases/{case_id}/feedback` chấp nhận `snapshot_hash` tùy ý từ client mà không đối chiếu với case hash, phá vỡ tính toàn vẹn chứng cứ (`apps/case_api/main.py:339`).
6. **FINDING-006 (HIGH):** Citation validation chỉ kiểm tra ID membership mà không kiểm tra số tiền; route `GET /workbench` không idempotent, gọi lại LLM trả phí sau mỗi lần đọc (`src/fincrime/agent/workflow.py:167-172`, `apps/case_api/main.py:460`).
7. **FINDING-007 (HIGH):** Ứng dụng React không thể kết nối tới backend FastAPI do thiếu reverse proxy trong `vite.config.ts`; Playwright test pass giả tạo nhờ mock mạng (`apps/investigator-web/vite.config.ts`).
8. **FINDING-008 (MEDIUM):** `TrainingRunState` là enum validator rỗng không kích hoạt huấn luyện hay kiểm tra gate; `baseline.json` chứa hash giả (`aaa...`); cờ `tests_passed` trong manifest là boolean tự khai (`src/fincrime/training/runner.py:27-42`, `src/fincrime/release/manifest.py:132`).
9. **FINDING-009 (MEDIUM):** Xung đột thẩm quyền giữa tài liệu 29/08 và `docs/architecture/README.md` về vai trò GraphSAGE; tuyên bố 100% coverage trong báo cáo lịch sử là không có căn cứ đo lường.

---

## 8. Lộ trình Khắc phục 4 Giai đoạn & Tiêu chí Nghiệm thu (Remediation Roadmap)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        LỘ TRÌNH KHẮC PHỤC THEO THỨ TỰ PHỤ THUỘC                        │
├───────────┬──────────────────────────────────────────┬─────────────────────────────────┤
│ Giai đoạn │ Hạng mục công việc cốt lõi               │ Rủi ro được giải quyết          │
├───────────┼──────────────────────────────────────────┼─────────────────────────────────┤
│ Phase 1   │ Sửa thuật toán Deep Trace & Lưu SQLite   │ Nhân quả thời gian & Mất dữ liệu│
│ Phase 2   │ Khắc phục nạp Corpus & Proxy Vite dev    │ Đồ thị rỗng & Đứt gãy giao diện │
│ Phase 3   │ Cache giả thuyết LLM & Khóa Feedback Hash│ Tiêu tốn chi phí & Giả mạo hash │
│ Phase 4   │ Chốt ADR kiến trúc & Tự động hóa Manifest│ Xung đột thẩm quyền & Test giả  │
└───────────┴──────────────────────────────────────────┴─────────────────────────────────┘
```

### Chi tiết nghiệm thu từng giai đoạn:
- **Phase 1 (Cốt lõi):**
  - Cập nhật `generate_candidates`: Lưu `inflow_time` và chỉ duyệt cạnh có `outflow_time >= inflow_time`. Bổ sung phân bổ ngân sách cạnh theo nhánh để phát hiện smurfing.
  - Xây dựng tầng lưu trữ SQLite cục bộ (`src/fincrime/cases/sqlite_store.py`) lưu dữ liệu bền vững xuống `data/fincrime_local.db`.
  - *Nghiệm thu:* Chạy lại Probe 8: loại bỏ cạnh 09:00; smurfing recall $\ge 80\%$. Restart server không làm mất case.
- **Phase 2 (Tích hợp):**
  - Thêm cấu hình reverse proxy trong `vite.config.ts` điều hướng `/cases` sang `127.0.0.1:8000`. Cập nhật `api.ts` kiểm tra HTTP status code trước khi cast kiểu.
  - Sửa `populate_corpus_fixtures` đọc đúng khóa `graphEdges` và `traceEdgeIds`; loại bỏ `except: pass` nuốt lỗi.
  - *Nghiệm thu:* Mở trình duyệt thật tải thành công dữ liệu từ backend port 8000. Probe 3 nạp đủ 10 case với đầy đủ node/edge.
- **Phase 3 (Bảo vệ & Tối ưu):**
  - Thêm cache giả thuyết theo `snapshot_hash` tại `GET /cases/{id}/workbench`.
  - Trong `CaseService.append_feedback`, bắt buộc `req.snapshot_hash == case.snapshot_hash`.
  - *Nghiệm thu:* Hai lần gọi `GET /workbench` chỉ gọi LLM 1 lần. Gửi hash sai bị từ chối 422.
- **Phase 4 (Quản trị):**
  - Ban hành ADR xác nhận chuẩn Local-First V1, hạ cấp GraphSAGE thành thử nghiệm.
  - Cập nhật `build_release_manifest` đọc trực tiếp kết quả từ `pytest.xml`, từ chối nếu có lỗi. Cài đặt `pytest-cov` vào CI.
  - *Nghiệm thu:* Manifest tự trích xuất số test pass từ XML; từ chối niêm phong nếu thiếu file test receipt.

---

## 9. Phán quyết Sẵn sàng (Readiness Verdict)

$$\mathbf{READINESS\_VERDICT} = \mathbf{WITH\_FIXES}$$

Hệ thống Financial Crime Intelligence Platform sở hữu nền tảng toán học và kỷ luật mật mã xuất sắc ở các module độc lập (bit-exact parity, SHA-256 immutability). Tuy nhiên, dự án **chưa thể phát hành ra môi trường production hoặc thử nghiệm điều tra viên thực tế** cho đến khi hoàn thành ít nhất Phase 1 và Phase 2 của lộ trình khắc phục trên.
