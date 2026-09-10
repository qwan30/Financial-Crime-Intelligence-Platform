# Đặc tả Thiết kế & Tương tác: Bàn cờ Điều tra Đồ thị Tội phạm Tài chính (Forensic Graph Canvas & Interaction Specification)

**Mã tài liệu:** `SPEC-AML-CANVAS-2026-01`
**Ngày ban hành:** 2026-09-08
**Trạng thái:** `APPROVED_DESIGN`
**Định vị kiến trúc:** Palantir Gotham / Chainalysis Reactor / Maltego Investigation Archetype
**Mục tiêu áp dụng:** Giao diện điều tra viên (`apps/investigator-web`) kết nối cùng Backend FastAPI (`apps/case_api`) và cơ sở dữ liệu PostgreSQL 17

---

## 1. Bối cảnh & Tầm nhìn Thiết kế (Design Context & Vision)

### 1.1. Hiện trạng & Lý do thay đổi
- **Hiện trạng cũ:** Khu vực đồ thị trong `CaseWorkspace.tsx` bị giam trong một thẻ `div` cao cố định 340px. Dữ liệu là các nút tròn nhỏ với nhãn chữ thả trôi bên ngoài, dễ va chạm chồng chéo khi có nhiều nút. Khi chọn layout đồng tâm (Concentric), toàn bộ đồ thị bị co rúm thành một cụm unreadable ở giữa màn hình. Toàn bộ mạng lưới hiển thị tĩnh (read-only), thiếu các công cụ điều khiển điều tra thực tế.
- **Tầm nhìn mới:** Nâng cấp khu vực đồ thị thành một **Bàn cờ điều tra tội phạm tài chính chuyên nghiệp (Forensic Graph Canvas)**. Canvas là trung tâm tác chiến của điều tra viên, cho phép trực quan hóa thứ tự nhân quả thời gian của dòng tiền, phát hiện thủ đoạn chia nhỏ (smurfing), ghim chứng cứ pháp lý trực tiếp vào hồ sơ SAR và tương tác mượt mà không bị rối loạn thị giác (hairball).

### 1.2. Bố cục Không gian (Workspace Spatial Layout)
Giao diện chuyển đổi sang mô hình **Split-Pane chuyên dụng**:
* **Khu vực Canvas Tác chiến (65% chiều rộng, 100% viewport height):**
  - Chiếm toàn bộ không gian bên trái, loại bỏ hoàn toàn giới hạn 340px.
  - Phía trên có thanh công cụ nổi (Floating Glass Toolbar) chứa bộ chuyển Layout, lọc ngưỡng tiền và phóng vừa màn hình.
  - Phía dưới có thanh trượt thời gian (Temporal Scrubber Bar) điều khiển diễn hoạt dòng tiền theo thời gian thực.
* **Ngăn Kéo Tra cứu & Hồ sơ Chứng cứ (35% chiều rộng bên phải):**
  - Chi tiết thực thể đang chọn (Chủ tài khoản, Ngân hàng, Số tài khoản, Điểm rủi ro ML, Vai trò mạng lưới).
  - Danh mục chứng cứ đã ghim vào hồ sơ SAR (Pinned Evidence Dossier).
  - Khối trợ lý AI (DeepSeek Copilot) tự động cập nhật giả thuyết vụ án theo các chứng cứ đã ghim.

---

## 2. Trụ cột 1: Thực thể Nút & Chống Va chạm Nhãn (Entity Node Cards & Zero Collision)

```
┌────────────────────────────────────────────────────────┐
│  Nguyễn Văn A                              [⚡ CHIA NHỎ]│
│  Vietcombank • 0451...2891                 Risk: 0.88  │
└────────────────────────────────────────────────────────┘
  ▲ 170px rộng, 52px cao — Toàn bộ nhãn nằm TRỌN BÊN TRONG card
```

### 2.1. Cấu trúc Thẻ Nút (Card Node Architecture)
Để chấm dứt vĩnh viễn lỗi chữ đè lên nhau khi các nút ở gần, hệ thống cấm tuyệt đối việc thả trôi nhãn chữ bên ngoài nút (`text-valign: bottom`). Mọi nút trên canvas được đóng gói thành **Thẻ thực thể hình chữ nhật bo góc (Entity Card)**:
- **Kích thước:** Chiều rộng chuẩn 170px, chiều cao chuẩn 52px, bo góc viền 6px.
- **Bố cục nhãn 2 dòng bên trong thẻ:**
  - *Dòng 1 (In đậm, màu trắng `#f8fafc`):* Tên chủ tài khoản hoặc tên đơn vị (ví dụ: `Nguyễn Văn A`, `Cty TNHH Nam Phát`, `Cây ATM VCB Q.1`).
  - *Dòng 2 (Màu xám bạc `#94a3b8`, font monospace):* Tên viết tắt ngân hàng và 4 số cuối tài khoản (ví dụ: `Vietcombank • 2891`, `Sacombank • 9020`).

### 2.2. Hệ thống Màu sắc & Phân cấp Trực quan (Color System - OKLCH / Slate Dark)
- **Nền thẻ:** Nền tối công nghiệp `#131b2e` (tương phản cao với nền canvas `#07090e`).
- **Phân loại rủi ro theo màu viền (Border Color Coding):**
  - **Tài khoản Hạt nhân (Seed Entity):** Viền màu xanh Neon Cyan (`#38bdf8`), độ dày viền 3px, nền đổi sang `#0c233c`, có hiệu ứng đổ bóng phát sáng 25px (`box-shadow: 0 0 25px rgba(56, 189, 248, 0.4)`).
  - **Rủi ro Nguy cấp (Risk Score $\ge 0.85$):** Viền đỏ Rose (`#f43f5e`), độ dày 2px.
  - **Rủi ro Đáng ngờ (Risk Score $0.50 - 0.85$):** Viền vàng hổ phách Amber (`#f59e0b`), độ dày 2px.
  - **Tài khoản Ngữ cảnh / Lành tính (Benign / Low Risk $< 0.50$):** Viền xám Slate (`#334155`), nền xám chìm `#0a0f1d`, nhãn chữ làm mờ để không tranh chấp thị giác với các nút tội phạm.

### 2.3. Huy hiệu Nhận diện Hành vi (Typology Badges)
Mỗi tài khoản được gắn nhãn nhận diện hành vi trong thuộc tính `badge` hiển thị tại góc trên bên phải thẻ:
- `🚩 SEED / HUB`: Trạm gom tiền hoặc hạt nhân điều tra.
- `⚡ SMURFING`: Tài khoản chia nhỏ số tiền dưới ngưỡng báo cáo.
- `🏢 SHELL CORP`: Công ty bình phong dùng để luân chuyển dòng tiền lớn.
- `🔄 LAYERING`: Tài khoản trung chuyển tầng 2, tầng 3.
- `🏧 CASHOUT`: Cây ATM hoặc điểm rút tiền mặt.
- `🌐 CRYPTO OTC`: Đại lý / thương nhân P2P sàn tiền mã hóa.
- `💡 / 🛒 BENIGN`: Hóa đơn điện nước, thương mại điện tử lành tính.

---

## 3. Trụ cột 2: Cạnh Giao dịch & Hiệu ứng Dòng chảy (Edge Linkages & Flow Motion)

### 3.1. Phân cấp Trọng số Đường Cạnh (Edge Width Encoding)
Độ dày của đường chuyển tiền phản ánh trực quan quy mô giá trị dòng tiền:
- **Giao dịch rất lớn ($\ge 100 \text{ triệu VND}$):** Chiều rộng 4.5px.
- **Giao dịch trung bình ($\ge 40 \text{ triệu VND}$):** Chiều rộng 3.0px.
- **Giao dịch nhỏ lẻ ($< 40 \text{ triệu VND}$):** Chiều rộng 1.8px.

### 3.2. Nhãn Cạnh Tránh Va chạm (Collision-Free Edge Labels)
- Mỗi cạnh hiển thị số tiền rút gọn và mốc thời gian: `48.5 tr (08:30)`.
- Nhãn cạnh được bao bọc bởi một hộp nền tối (`text-background-color: #07090e`), độ mờ 90%, viền 1px bo góc tròn. Nhãn tự động xoay theo góc nghiêng của đường nối (`text-rotation: autorotate`), đảm bảo chữ không bao giờ bị đường kẻ cắt ngang qua.

### 3.3. Hiệu ứng Ghim Bằng chứng Báo cáo SAR (Evidence Pinning Interaction)
- **Thao tác:** Điều tra viên click vào một mũi tên giao dịch $\rightarrow$ Bảng bên phải hiển thị chi tiết giao dịch kèm nút **`📌 Ghim Giao Dịch Này vào Hồ Sơ SAR`**.
- **Hiệu ứng tức thì (Instant Feedback):**
  - Cạnh chuyển ngay sang **màu tím dạ quang Neon Violet (`#c084fc`)**.
  - Đầu mũi tên và viền nhãn chuyển sang tím phát sáng (`box-shadow: 0 0 16px rgba(192, 132, 252, 0.4)`).
  - Bản ghi tự động được thêm vào danh sách **Chứng cứ đã ghim** ở Drawer bên phải với nhãn `GHIM SAR`.
  - Một API request `POST /cases/{case_id}/evidence/pin` được gửi xuống PostgreSQL để lưu trữ vĩnh viễn.

### 3.4. Hiệu ứng Tiêu điểm & Làm mờ Ngữ cảnh (Focus & Dimming)
- Khi điều tra viên click chọn bất kỳ một nút nào:
  - Hệ thống tự động làm mờ toàn bộ các nút và cạnh không liên quan xuống mức `opacity: 0.20`.
  - Làm sáng rực rỡ (`opacity: 1.0`) tập hợp lân cận đóng (closed neighborhood) và đường dẫn nối từ tài khoản Hạt nhân (Seed) tới nút đó.
  - Bấm nút **`⛶ Phóng vừa (F)`** hoặc click ra ngoài khoảng trống canvas để hủy làm mờ.

---

## 4. Trụ cột 3: Thanh trượt Thời gian & Mô phỏng Diễn biến (Temporal Scrubber & Playback)

```
[ ▶ Play ]  09:15:00  ───○─────────────────────────────────[ 100% ]  [ Tốc độ: 1.0x ]
           08:15      08:30      09:00      09:20      09:45
```

### 4.1. Bản chất Nghiệp vụ của Dòng chảy Thời gian
Tội phạm tài chính luôn hoạt động theo chuỗi nhân quả: *Tiền vào trước $\rightarrow$ Tiền ra sau*. Hệ thống bắt buộc phải thể hiện được yếu tố thời gian thay vì trình bày một bức tranh phẳng chết cứng.

### 4.2. Thanh trượt Dòng thời gian (Time-Range Slider)
- Đặt ở đáy màn hình với chiều cao 64px, nền kính mờ `#0d1322` chống lóa.
- **Thanh trượt thời gian:** Đại diện cho trục thời gian từ giao dịch đầu tiên ($T_{\min}$) đến giao dịch cuối cùng ($T_{\max}$).
- **Cơ chế lọc cạnh:** Khi kéo thanh trượt đến mốc $T$, Cytoscape chỉ hiển thị các giao dịch thỏa mãn:
  $$\text{edge.timestamp} \le T$$
  Các giao dịch diễn ra trong tương lai sau mốc $T$ tự động ẩn (`display: none`).

### 4.3. Mô phỏng Tự động (Playback Simulation)
- Nút bấm **`Play (▶)`** (hỗ trợ phím tắt `Space`):
  - Tự động di chuyển con trượt thời gian từ $0\% \rightarrow 100\%$ theo chu kỳ nhịp nhàng.
  - Người dùng chứng kiến tiền chảy tuần tự:
    1. *08:15:* Giao dịch trả tiền điện EVN diễn ra bình thường.
    2. *08:30 – 08:55:* Ba tài khoản con la chuyển tiền dồn dập vào tài khoản trạm gom.
    3. *09:12:* Trạm gom chuyển một khoản tiền lớn 140 triệu vào công ty bình phong.
    4. *09:35 – 09:50:* Tiền bốc hơi ra cây ATM và sàn giao dịch P2P Crypto.
- **Nút đổi tốc độ (`Tốc độ: 1.0x`):** Cho phép đổi bước nhảy giữa `1.0x`, `2.0x`, và `4.0x`.

---

## 5. Trụ cột 4: Cơ chế Chống rối Bụi gai & Mở rộng Từng bước (Anti-Hairball & Progressive Discovery)

Khi một vụ án có hàng trăm đối tượng, canvas bắt buộc phải kích hoạt 4 cơ chế chống quá tải thị giác:

### 5.1. Gom cụm Tài khoản Con la (Compound Node Clustering)
- Khi phát hiện một nhóm $\ge 5$ tài khoản có cùng hành vi (cùng gửi tiền dưới 50 triệu vào một trạm trong 1 giờ), Cytoscape tự động gộp chúng thành **1 nút phức hợp duy nhất**:
  ```
  [ 👥 Cụm 12 Con la Nạp tiền • Tổng: 580.0 tr ]
  ```
- **Tương tác:** Nhấp đúp (Double-click) vào nút cụm để bung ra 12 nút con; nhấp đúp lần nữa để thu gọn lại.

### 5.2. Bộ lọc Ngưỡng tiền Thuần Hiển thị & Có thể Đảo ngược (Reversible View-Only Amount Filter)
- **Nguyên lý nghiệp vụ AML cốt lõi:** **Quy mô số tiền không quyết định tính chất lành tính hay tội phạm.** Các giao dịch giá trị thấp chính là thủ đoạn **Smurfing (chia nhỏ dòng tiền)** mà hệ thống này được xây dựng để phát hiện. Việc lọc bỏ các món tiền nhỏ nếu làm sai có thể vô tình "giúp" kẻ rửa tiền ẩn mình khỏi tầm mắt của điều tra viên.
- **Ràng buộc thiết kế bắt buộc:**
  - **Bộ lọc thuần hiển thị (View-Only & Reversible):** Thanh trượt ngưỡng tiền (`0 VND` đến `100,000,000 VND`) chỉ thay đổi trạng thái ẩn/hiện tạm thời trên canvas. **Tuyệt đối không xóa bằng chứng, không loại bỏ cạnh khỏi dữ liệu nền tảng của vụ án, và không bao giờ tự động gán nhãn lại (relabel) các giao dịch bị ẩn thành "lành tính".**
  - **Chỉ báo cạnh và số tiền bị ẩn (Visible Hidden-Edge Indicators):** Khi các giao dịch bị ẩn do nằm dưới ngưỡng lọc, các nút liên quan **bắt buộc phải hiển thị huy hiệu chỉ báo cạnh ẩn** (ví dụ: badge `[Ẩn: 3 txs • 4.5 tr]`). Điều tra viên luôn nhìn thấy sự hiện diện của dòng tiền ngầm, không bao giờ bị đánh lừa rằng nút đó không có giao dịch.
  - **Bảo toàn khả năng phát hiện nhánh Smurfing (Smurfing Discoverability):** Khi click vào chỉ báo cạnh ẩn trên nút hoặc xem Drawer chi tiết, điều tra viên có thể duyệt danh sách các giao dịch vi mô bị lọc và bấm chọn *"Ghim hiển thị nhánh này"* (Override Filter / Pin to View) để giữ nguyên nhánh nghi vấn trên canvas bất kể ngưỡng lọc số tiền chung.
### 5.3. Mở rộng Từng bước (Progressive Hop Expansion - 3-Hops Rule)
- Không bao giờ nạp toàn bộ cơ sở dữ liệu lên màn hình.
- Khởi đầu vụ án: Mặc định chỉ nạp **Seed và 1-Hop lân cận** (tài khoản hạt nhân và những người trực tiếp chuyển/nhận tiền với người đó).
- Nút bấm **`➕ Mở rộng Hop`** trên thanh công cụ: Khi click, hệ thống gửi request tới Backend API để nạp tiếp tầng F2, F3 của đối tượng đang được chọn.

---

## 6. Trụ cột 5: Bộ chuyển đổi Bố cục Đồ thị (Layout Engines)

Hệ thống hỗ trợ 3 chế độ dàn trang được tối ưu hóa tham số chống co cụm:

| Tên Bố cục | Thuật toán sử dụng | Mục đích nghiệp vụ | Cấu hình tham số chống va chạm |
|---|---|---|---|
| **Dòng tiền Nhân quả (Mặc định)** | Custom Dagre / Step-column | Xếp theo 4 cột ngang từ Trái sang Phải theo thứ tự nhân quả thời gian: Con la $\rightarrow$ Trạm gom $\rightarrow$ Bình phong $\rightarrow$ Cashout. | Tọa độ cột cố định: `colX = [120, 430, 740, 1050]`, khoảng cách giữa các cột $\ge 300px$. Tuyệt đối 0% va chạm nhãn. |
| **Gom cụm Tổ chức** | CoSE (Compound Spring Embedder) | Tự động kéo các tài khoản có giao dịch qua lại dày đặc lại gần nhau, đẩy các tài khoản vãng lai ra xa. | `nodeRepulsion: 900000`, `idealEdgeLength: 200`, `padding: 80`. Lực đẩy cực đại ngăn ngừa nút chụm vào nhau. |
| **Tỏa tròn (Đồng tâm rộng)** | Concentric Layout | Đặt tài khoản Hạt nhân ở tâm điểm, các bước nhảy 1-hop, 2-hop nằm trên các vòng tròn đồng tâm mở rộng. | `concentric`: Seed=3, F1=2, Context=1; `minNodeSpacing: 140`, `padding: 90`. Khắc phục triệt để lỗi co cụm của bản cũ. |

---

## 7. Giao thức Tích hợp Backend & Lưu trữ Bền vững (API & Persistence Contract)

### 7.1. Cấu hình Reverse Proxy Gateway (Sửa lỗi Finding 7)
Tệp `apps/investigator-web/vite.config.ts` bắt buộc khai báo proxy để điều hướng các cuộc gọi API từ cổng 5173 sang server FastAPI cổng 8000:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/cases': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
});
```

### 7.2. Bền vững hóa Vị trí Nút (Persisted Graph Coordinates)
- Khi điều tra viên kéo thả các thẻ nút để dàn trang bàn cờ điều tra theo ý muốn, tọa độ `{ x, y }` của từng nút được lưu tự động vào `localStorage` theo khóa `graph_pos_{case_id}` (hoặc lưu vào bảng `cases.layout_json` trong PostgreSQL).
- Khi mở lại vụ án, đồ thị nạp lại đúng vị trí điều tra viên đã sắp xếp, không bị thuật toán tự động reset lung tung.

### 7.3. Hợp đồng API Ghim Chứng cứ (Evidence Pinning Contract)
* **Endpoint:** `POST /cases/{case_id}/evidence/pin`
* **Request Payload:**
  ```json
  {
    "edge_id": "TXN-2026-8804",
    "analyst_id": "analyst_01",
    "is_pinned": true,
    "typology_tag": "CASHOUT"
  }
  ```
* **Phản hồi:** Trả về mã băm vụ án cập nhật `new_snapshot_hash` và lưu bản ghi vào bảng `case_evidence` trong PostgreSQL.

---

## 8. Phím tắt Thao tác Nhanh (Keyboard Accessibility)

Để hỗ trợ điều tra viên thao tác liên tục bằng bàn phím theo chuẩn `impeccable`:
- **`Space`:** Bật / Dừng mô phỏng dòng tiền (Play / Pause).
- **`F` hoặc `f`:** Phóng vừa toàn bộ đồ thị vào giữa màn hình (Fit to screen).
- **`P` hoặc `p`:** Ghim / Bỏ ghim giao dịch đang chọn vào báo cáo SAR.
- **`1`, `2`, `3`:** Chuyển đổi nhanh giữa các Layout: Dòng tiền nhân quả (`1`), Gom cụm (`2`), Tỏa tròn (`3`).
- **`Delete` / `Backspace`:** Ẩn tạm thời nhánh giao dịch đang chọn khỏi màn hình làm việc.

---

## 9. Tiêu chuẩn Nghiệm thu Kỹ thuật (Acceptance Verification)

Tất cả các thành phần triển khai theo đặc tả này phải vượt qua các tiêu chí nghiệm thu sau:
1. **Tiêu chí Không Va chạm (Zero Collision):** Mọi văn bản tên tài khoản, số tiền và thời gian phải hiển thị nguyên vẹn, khoảng cách lề tối thiểu $\ge 12px$, không có bất kỳ nhãn nào đè lên nhau ở độ phân giải $1440 \times 900$ và $1920 \times 1080$.
2. **Tiêu chí Nhân quả Thời gian:** Thanh trượt thời gian tại bất kỳ mốc $T$ nào chỉ hiển thị các giao dịch có $\text{timestamp} \le T$. Tuyệt đối không cho phép giao dịch trong tương lai xuất hiện trước.
3. **Tiêu chí Ghim Bằng chứng:** Thao tác ghim cạnh phải đổi màu tím dạ quang ngay lập tức trên canvas và đồng bộ dữ liệu với danh mục chứng cứ SAR ở ngăn kéo bên phải.
4. **Tiêu chí Tính toàn vẹn Dữ liệu:** Toàn bộ tên ngân hàng, số tài khoản che mờ, số tiền bằng triệu đồng VND phải tuân thủ đúng chuẩn giao dịch liên ngân hàng Việt Nam (Napas 24/7).
5. **Tiêu chí Bảo toàn Nhánh Smurfing khi Lọc:** Kiểm thử trường hợp nhánh rửa tiền chia nhỏ giá trị thấp (ví dụ: các món 10–45 triệu) vẫn hiển thị chỉ báo số lượng/tổng tiền bị ẩn trên nút khi kéo thanh lọc lên mức 50 triệu; không có bằng chứng nào bị xóa hay bị phân loại lại thành "lành tính"; điều tra viên có thể bung mở lại nhánh đó trực tiếp từ canvas.
