# Pain point ngân hàng Việt Nam và cơ hội sản phẩm thực dụng

**Ngày:** 29/08/2026
**Phạm vi:** Việt Nam, bằng chứng chủ yếu giai đoạn 2024–2026
**Đối tượng:** khách hàng cá nhân, hộ kinh doanh/SME, nhân viên vận hành và tuân thủ ngân hàng
**Mục tiêu:** chọn vấn đề có người dùng thật, giải pháp tối thiểu có thể kiểm chứng bởi một nhóm nhỏ; không đề xuất sản phẩm cho vay, tư vấn thuế/pháp lý hay quyết định AML tự động.

## Kết luận điều hành

Thị trường không thiếu ứng dụng ngân hàng, cổng QR, eKYC hay mô hình phát hiện gian lận. Khoảng trống đáng làm nằm ở các **workflow ngoại lệ**: khi người dùng vừa chuyển tiền cho kẻ gian, khi hộ kinh doanh phải ghép giao dịch với hóa đơn/chứng từ, hoặc khi chuyên viên AML phải chứng minh một báo cáo là đầy đủ và có căn cứ.

Ba cơ hội đáng xem xét nhất:

1. **Fraud Incident & Tra-soát Evidence Assistant** — phù hợp nhất với repo hiện tại và hữu ích trực tiếp cho người vừa bị lừa/chuyển nhầm.
2. **Transaction–Invoice Compliance Companion cho hộ kinh doanh** — pain được lượng hóa mạnh nhất và dễ phỏng vấn người dùng nhất, nhưng phải chọn một workflow hẹp vì MISA, SePay và payOS đã hiện diện.
3. **STR/KYC Evidence Quality Gate** — phù hợp với áp lực FATF và Thông tư 27/2025/TT-NHNN, nhưng chỉ nên làm khi có một đơn vị báo cáo hoặc chuyên viên AML làm design partner.

Không nên tiếp tục xây một “AML platform đầy đủ” gồm GNN, Kafka, Neo4j, case management và copilot. Những thành phần đó đã có nhiều nhà cung cấp; chúng không giải quyết được rào cản tiếp cận dữ liệu và triển khai tại ngân hàng.

## 1. Những pain point có bằng chứng mạnh

### 1.1 Lừa đảo số: phòng ngừa đã tiến bộ, xử lý sau sự cố vẫn khó

Ngân hàng số đã trở thành kênh chính: NHNN cho biết nhiều tổ chức tín dụng có trên 90% giao dịch qua kênh số và hơn 87% người trưởng thành có tài khoản ngân hàng. [NHNN, Chuyển đổi số ngành Ngân hàng 2025](https://www.sbv.gov.vn/w/sbv637421)

Sinh trắc học và làm sạch tài khoản có hiệu quả đáng kể: theo báo cáo các tổ chức tín dụng, số vụ khách hàng cá nhân mất tiền trong giai đoạn 01/07–30/11/2024 giảm khoảng 68%, còn số tài khoản nhận tiền lừa đảo giảm khoảng 64% so với mức bình quân sáu tháng đầu năm. Đây là quan sát trước–sau, không phải bằng chứng nhân quả, nhưng cho thấy không nên xây thêm một lớp eKYC chung chung. [NHNN, an ninh an toàn ngân hàng số](https://www.sbv.gov.vn/vi/web/sbv_portal/w/sbv622854)

Pain vẫn còn lớn: Bộ Công an ghi nhận khoảng 17.200 vụ lừa đảo trên không gian mạng từ năm 2022 đến tháng 10/2025 với hàng trăm nghìn nạn nhân; chính cơ quan này nêu khó khăn về hợp tác liên ngành, truy vết dòng tiền và thu hồi tài sản. [Bộ Công an, Hội thảo quốc gia 29/12/2025](https://www.bocongan.gov.vn/bai-viet/chung-tay-phong-chong-toi-pham-lua-dao-chiem-doat-tai-san-tren-khong-gian-mang-1767000704)

Ngày 23/06/2026, Bộ Công an và NHNN mới ký quy chế phối hợp nhằm chuyển từ xử lý từng vụ sang phối hợp thường xuyên, có đầu mối, quy trình và công cụ kỹ thuật; các ưu tiên gồm xác minh, phong tỏa và truy vết dòng tiền nhanh. Điều này chứng minh “handoff sau sự cố” là vấn đề vận hành đang được giải quyết, không chỉ là ý tưởng sản phẩm. [Bộ Công an–NHNN, Quy chế phối hợp 2026](https://www.bocongan.gov.vn/bai-viet/bo-cong-an-va-ngan-hang-nha-nuoc-viet-nam-ky-ket-quy-che-phoi-hop-trong-cong-tac-phong-chong-lua-dao-truc-tuyen-1782217322)

nTrust đã cung cấp miễn phí việc kiểm tra số điện thoại, số tài khoản, link, QR và gửi báo cáo cộng đồng trên cơ sở dữ liệu hơn một triệu bản ghi. Vì vậy, một blacklist hoặc app “check scam” mới sẽ khó tạo giá trị. Danh mục tính năng công khai của nTrust không mô tả luồng tạo hồ sơ tra soát, chuẩn hóa chứng cứ hay theo dõi tiến độ sau khi tiền đã chuyển; đây là **khoảng trống suy luận từ phạm vi sản phẩm công khai**, chưa phải bằng chứng rằng không có hệ thống nội bộ nào làm việc đó. [Cổng Chính phủ, nTrust](https://baochinhphu.vn/ra-mat-phan-mem-phat-hien-dau-hieu-lua-dao-qua-dien-thoai-102240730125149283.htm)

### 1.2 Hộ kinh doanh: giao dịch ngân hàng, hóa đơn và thuế không khớp thành một workflow dễ dùng

Báo cáo Kinh tế tư nhân Việt Nam 2025 của VCCI thu thập phản hồi từ hơn 1.000 hộ kinh doanh tại 34 tỉnh/thành. Trong nghiệp vụ thuế–kế toán, 71,2% đánh giá khó/rất khó khi thu thập thông tin khách hàng để xuất hóa đơn điện tử; 67,6% khó hạch toán chi phí được trừ; 62,3% khó kê khai và nộp thuế. Thời gian tuân thủ gây sức ép lớn/rất lớn với 73% hộ, chi phí thuê kế toán với 68%. [VCCI, Báo cáo Kinh tế tư nhân Việt Nam 2025, tr. 87–90 và 128](https://api.vcci.com.vn/storage/filesvcci/6a06e39373a14.pdf)

Các yêu cầu về hóa đơn, chứng từ và thanh toán không tiền mặt đã thay đổi nhanh trong 2025–2026 và còn phụ thuộc loại thuế, ngưỡng doanh thu và bối cảnh giao dịch. Một số hướng dẫn năm 2026 dùng mốc 5 triệu đồng cho chi phí của một số hộ kinh doanh, trong khi hướng dẫn khác dùng mốc 20 triệu đồng cho một số trường hợp thuế giá trị gia tăng. Vì vậy sản phẩm không được hard-code một “luật chung”; rule phải có phiên bản, ngày hiệu lực, nguồn và bước xác nhận của kế toán. [Cổng Chính phủ, hướng dẫn chi phí hộ kinh doanh](https://xaydungchinhsach.chinhphu.vn/nhung-luu-y-ve-chi-phi-hop-le-trong-thanh-toan-thue-cua-ho-kinh-doanh-119260319172335943.htm), [hướng dẫn hóa đơn 2026](https://xaydungchinhsach.chinhphu.vn/quy-dinh-moi-ve-thue-va-hoa-don-dien-tu-trong-thuong-mai-dien-tu-va-ban-hang-da-kenh-119260717133903995.htm)

SePay, payOS/Casso và MISA đã giải quyết nhiều phần của thanh toán, đối soát, hóa đơn và vay dựa trên dữ liệu. Do đó cơ hội không phải một phần mềm kế toán/QR mới, mà là một workflow nhỏ cho nhóm chưa dùng hệ sinh thái lớn: nhập sao kê CSV, ghép giao dịch–hóa đơn–chứng từ, đánh dấu khoản chưa đủ bằng chứng và xuất gói bàn giao cho kế toán. [SePay Bank Hub](https://developer.sepay.vn/bankhub/tong-quan), [payOS](https://payos.vn/), [MISA Lending](https://lending.misa.vn/)

### 1.3 SME: khó vay phần nhiều vì hồ sơ, dòng tiền và tài sản bảo đảm

Khảo sát PCI 2025 cho thấy 52,2% doanh nghiệp gặp khó khăn khi tìm nguồn vốn. Trong số doanh nghiệp trả lời câu hỏi về vay vốn tại địa phương, 75,5% đồng ý rằng không thể vay nếu không có tài sản thế chấp, 54,2% cho rằng vay không thế chấp rất khó và 45% đánh giá thủ tục vay phiền hà. Đây là cảm nhận doanh nghiệp, không phải tỷ lệ từ chối hồ sơ ngân hàng, nhưng đủ mạnh để xác nhận pain “credit readiness”. [VCCI, Báo cáo Kinh tế tư nhân Việt Nam 2025, tr. 47 và 53–54](https://api.vcci.com.vn/storage/filesvcci/6a06e39373a14.pdf)

Nghị định 94/2025/NĐ-CP mở cơ chế thử nghiệm cho chấm điểm tín dụng, Open API và P2P lending. Điều này tạo đường thử nghiệm nhưng cũng có nghĩa một startup không nên tự triển khai credit scoring hoặc truy cập tài khoản như một tính năng thông thường. [Chính phủ, Nghị định 94/2025/NĐ-CP](https://vanban.chinhphu.vn/?docid=213519&pageid=27160)

Cơ hội khả thi là **vendor-neutral credit evidence passport**, không phải mô hình quyết định tín dụng: gom dữ liệu do doanh nghiệp chủ động xuất, lập bảng dòng tiền/công nợ, chỉ ra tài liệu thiếu và tạo gói có nguồn gốc để gửi nhiều ngân hàng. Điểm yếu là MISA Lending đã có lợi thế dữ liệu và đối tác ngân hàng lớn; chỉ nên làm nếu tìm được phân khúc không dùng MISA hoặc một ngành có chứng từ đặc thù.

### 1.4 AML/KYC/STR: áp lực thật nhưng generic AML platform đã đông

Đến ngày 19/06/2026, Việt Nam vẫn thuộc danh sách giám sát tăng cường của FATF và toàn bộ thời hạn trong action plan đã hết từ tháng 05/2025. Các thiếu hụt còn lại gồm risk-based supervision, CDD/STR, thông tin chủ sở hữu hưởng lợi và chất lượng/số lượng phân tích tài chính. [FATF, danh sách giám sát tăng cường tháng 06/2026](https://www.fatf-gafi.org/en/publications/High-risk-and-other-monitored-jurisdictions/increased-monitoring-june-2026.html)

Thông tư 27/2025/TT-NHNN có hiệu lực từ 01/11/2025, thay Thông tư 09/2023, cập nhật quản lý rủi ro, CDD, báo cáo giao dịch lớn, giao dịch đáng ngờ và chuyển tiền điện tử. Báo cáo điện tử và các phụ lục biểu mẫu hiện đã công khai. [Cơ sở dữ liệu quốc gia về văn bản pháp luật, Thông tư 27/2025](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=182189&Keyword=), [Cổng AMLD của NHNN](https://aml.sbv.gov.vn/home?slug=huong-dan-ang-&view=GDTM)

Tuy nhiên FPT/Oracle và các nhà cung cấp lớn đã triển khai nền tảng AML tại ngân hàng Việt Nam. Khoảng trống phù hợp nhóm nhỏ là lớp **quality gate** chạy trước khi gửi báo cáo: kiểm tra trường bắt buộc, mâu thuẫn, nguồn chứng cứ, thay đổi giữa phiên bản và dấu vết phê duyệt. Nó không phát hiện rửa tiền, không tự quyết định báo cáo và không tự gửi STR. [FPT–MSB, dự án AML 2025](https://fpt-is.com/msb-va-fpt-khoi-dong-du-an-phong-chong-rua-tien-moi-hien-dai-hoa-quan-tri-rui-ro-tuan-thu-trong-hoat-dong-ngan-hang/)

### 1.5 Người dùng dễ bị tổn thương và accessibility

Luật Bảo vệ quyền lợi người tiêu dùng yêu cầu cơ chế khiếu nại phù hợp với người tiêu dùng dễ bị tổn thương. NHNN từng phải yêu cầu rà soát sau phản ánh người khuyết tật bị nhiều ngân hàng từ chối mở tài khoản nếu không có người giám hộ. Bằng chứng hiện chỉ là một vụ việc chính thức, nên cần discovery trước khi coi đây là thị trường lớn. [Bộ Công Thương, cơ chế bảo vệ người tiêu dùng dễ bị tổn thương](https://moit.gov.vn/tin-tuc/bao-chi-voi-nguoi-dan/co-che-bao-ve-quyen-loi-nguoi-tieu-dung-de-bi-ton-thuong-trong-luat-bao-ve-quyen-loi-nguoi-tieu-dung-sua-doi-the-hien-ch.html), [Cổng Chính phủ, người khuyết tật mở tài khoản](https://baochinhphu.vn/nguoi-khuyet-tat-mo-tai-khoan-co-can-nguoi-giam-ho-10224030609454955.htm)

Đây là cơ hội tốt cho một accessibility onboarding/support kit, nhưng chưa phải lựa chọn đầu tiên nếu chưa phỏng vấn người khuyết tật và nhân viên quầy.

## 2. Xếp hạng cơ hội

Điểm 1–5; cao hơn là tốt hơn. “Khoảng trống” đánh giá mức chưa bị sản phẩm hiện có bao phủ, không phải tuyên bố độc quyền hay novelty.

| Cơ hội | Pain | Giá trị trực tiếp | Khả thi nhóm nhỏ | Tiếp cận người dùng | Khoảng trống | Tổng /25 |
|---|---:|---:|---:|---:|---:|---:|
| Fraud incident & tra-soát evidence assistant | 5 | 5 | 5 | 4 | 4 | **23** |
| Transaction–invoice companion cho hộ kinh doanh | 5 | 5 | 4 | 5 | 2 | **21** |
| Vendor-neutral SME credit evidence passport | 5 | 5 | 4 | 4 | 2 | **20** |
| STR/KYC evidence quality gate | 5 | 4 | 4 | 2 | 4 | **19** |
| Loan/fee explainer + complaint locker | 3 | 4 | 5 | 4 | 2 | **18** |
| Accessible onboarding/support kit | 3 | 5 | 3 | 2 | 4 | **17** |

## 3. Khuyến nghị cho repository hiện tại

### Chọn: Fraud Incident & Tra-soát Evidence Assistant

**Người dùng chính:** khách hàng vừa chuyển nhầm hoặc nghi bị lừa; nhân viên tiếp nhận tra soát/fraud operations là người dùng thứ hai khi có design partner.

**Job to be done:** “Trong vài phút đầu sau sự cố, giúp tôi biết phải làm gì, gom đúng bằng chứng một lần và chuyển một hồ sơ nhất quán cho ngân hàng/cơ quan chức năng.”

**MVP bốn màn hình:**

1. Phân loại sự cố: tự chuyển do bị lừa, giao dịch không nhận biết, chuyển nhầm, lộ thiết bị/tài khoản.
2. Thu thập tối thiểu: ngân hàng, transaction ID, thời gian, số tiền, bên nhận, điện thoại/link/QR, chat, ảnh và sao kê.
3. Tạo timeline, chỉ ra bằng chứng còn thiếu và checklist hành động khẩn cấp theo từng loại sự cố.
4. Xuất một case pack PDF + JSON có hash, danh mục file, thông tin liên hệ và nhật ký trạng thái.

Văn bản hợp nhất 75/VBHN-NHNN năm 2026 yêu cầu tổ chức cung ứng dịch vụ có kênh tiếp nhận tra soát/khiếu nại, ghi âm hotline 24/7 và cho khách tra cứu tiến độ/kết quả trực tuyến. Sản phẩm có thể chuẩn hóa đầu vào cho quy trình này, nhưng không được tự nhận là kênh tra soát chính thức khi chưa có hợp tác. [Công báo, 75/VBHN-NHNN](https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-75-vbhn-nhnn-469884.htm)

**Không xây trong MVP:** blacklist, graph/GNN, tự phong tỏa, hứa thu hồi tiền, chatbot pháp lý, tự gửi tố giác hoặc kết nối ngân hàng giả lập như thật.

**Tại sao phù hợp máy hiện tại:** chủ yếu là form, workflow, mã hóa/hash, export và validation; không cần GPU, full AMLBench, Neo4j hay Kafka.

## 4. Lựa chọn dễ kiểm chứng thị trường hơn

### Transaction–Invoice Compliance Companion

Nếu mục tiêu là tìm người dùng trả tiền sớm thay vì giữ hướng financial crime, lựa chọn này dễ phỏng vấn và pilot hơn:

- nhập sao kê CSV của một ngân hàng;
- nhập hóa đơn/chứng từ từ một nguồn;
- ghép khoản thu/chi với chứng từ;
- hiển thị khoản chưa ghép, khoản thiếu bằng chứng và rule/source đang áp dụng;
- xuất gói bàn giao cho kế toán.

Chỉ chọn **một phân khúc và một workflow**. Ví dụ: hộ bán lẻ cần chốt sổ cuối ngày hoặc doanh nghiệp xây dựng cần theo dõi công nợ/thu tiền. Không xây POS, kế toán, cổng thanh toán hay vay vốn toàn diện.

## 5. Ý tưởng nên loại hoặc hoãn

- **Generic AML platform/GNN graph:** cạnh tranh cao, thiếu dữ liệu thật và chu kỳ bán hàng ngân hàng dài.
- **Public mule-account checker:** nTrust và SIMO đã có dữ liệu trung tâm; crowdsourcing độc lập dễ false positive và bị lạm dụng.
- **QR/payment reconciliation tổng quát:** SePay, payOS/Casso và ngân hàng đã cung cấp.
- **eKYC/sinh trắc học mới:** ngân hàng, FPT và dữ liệu dân cư đã chiếm phần cốt lõi.
- **Generic SME loan marketplace:** MISA Lending có data moat và nhiều đối tác.
- **AI chatbot tài chính chung:** ít khác biệt, rủi ro đưa lời khuyên sai và không giải quyết workflow cuối cùng.

## 6. Ràng buộc pháp lý và thiết kế tối thiểu

Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 có hiệu lực từ 01/01/2026. Trong tài chính–ngân hàng, chỉ được thu thập dữ liệu cần thiết; việc dùng thông tin tín dụng để chấm điểm/đánh giá tín nhiệm cần sự đồng ý của chủ thể. [Cổng Chính phủ, bảo vệ dữ liệu trong tài chính ngân hàng](https://xaydungchinhsach.chinhphu.vn/quy-dinh-bao-ve-du-lieu-ca-nhan-trong-hoat-dong-tai-chinh-ngan-hang-119250725172823942.htm)

Vì vậy mọi MVP nên:

- local-first hoặc mã hóa dữ liệu ở trạng thái lưu và truyền;
- không yêu cầu credential ngân hàng;
- chỉ nhận file do người dùng chủ động xuất;
- có consent rõ, thời hạn lưu và nút xóa toàn bộ;
- tách “thông tin từ nguồn” khỏi “suy luận của hệ thống”;
- không tự chấm điểm tín dụng, kết luận rửa tiền, nộp thuế hay hứa thu hồi tài sản.

## 7. Kế hoạch validation 14 ngày

### Nếu chọn Fraud Incident Assistant

- Phỏng vấn 5 người từng bị lừa/chuyển nhầm, 3 nhân viên CSKH hoặc fraud operations và 1 chuyên gia bảo vệ người tiêu dùng/an toàn mạng.
- Dùng dữ liệu giả hoặc đã che thông tin; không thu thập hồ sơ vụ án thật trong giai đoạn đầu.
- Prototype case pack bằng form, chưa cần AI.
- Gate tiếp tục: người dùng hoàn thành hồ sơ dưới 10 phút; reviewer tìm được giao dịch, timeline và bằng chứng chính mà không hỏi lại quá một vòng; không có lời hứa hoặc kết luận không có căn cứ.

### Nếu chọn Transaction–Invoice Companion

- Phỏng vấn 10 hộ kinh doanh và 3 kế toán dịch vụ.
- Chọn đúng một ngân hàng, một định dạng sao kê và một định dạng hóa đơn.
- Gate tiếp tục: ghép tự động ít nhất 80% giao dịch có tham chiếu rõ; giảm tối thiểu 50% thời gian chuẩn bị gói giao kế toán; mọi cảnh báo đều dẫn nguồn và ngày hiệu lực.

### Nếu chọn STR Evidence Gate

- Chỉ tiến hành khi có ít nhất 3 chuyên viên AML/đơn vị báo cáo đồng ý review workflow.
- Dùng biểu mẫu công khai của Thông tư 27 và case tổng hợp, không dùng dữ liệu ngân hàng thật.
- Gate tiếp tục: phát hiện được trường thiếu/mâu thuẫn mà không tự kết luận suspicious; giảm thời gian QA và giữ được audit diff.

## 8. Giới hạn nghiên cứu

- Dữ liệu công khai đo tốt quy mô số hóa, lừa đảo và áp lực tuân thủ, nhưng thiếu volume/SLA tra soát theo từng ngân hàng và willingness-to-pay.
- Một số thống kê là báo cáo hội thảo hoặc khảo sát tự khai; chúng được dùng như tín hiệu pain, không như ước lượng nhân quả.
- Khẳng định về khoảng trống sản phẩm dựa trên tính năng công khai; hệ thống nội bộ của ngân hàng có thể đã giải quyết một phần nhưng không công bố.
- Quy định thuế 2025–2026 thay đổi nhanh và khác nhau theo ngữ cảnh; cần kế toán/pháp chế xác nhận trước khi biến thành rule sản phẩm.

## Phương pháp và lý do dừng

Nghiên cứu ưu tiên NHNN, Bộ Công an, Chính phủ, FATF, VCCI và IFC; sau đó đối chiếu với tài liệu sản phẩm của các nhà cung cấp hiện hữu. Hai lane độc lập khảo sát khách hàng số/gian lận và SME/vận hành-tuân thủ, còn các claim quyết định được kiểm tra lại trực tiếp ở nguồn chính. Dừng khi nguồn mới lặp lại năm cụm pain và không làm thay đổi thứ tự shortlist. BrowserAct không dùng được vì môi trường chưa cấu hình API key; truy cập được thực hiện qua các nguồn web công khai ở chế độ chỉ đọc.
