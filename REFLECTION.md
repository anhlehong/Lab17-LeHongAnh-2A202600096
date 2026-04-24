# Phản ánh: Privacy, Rủi ro và Hạn chế

## 1. Memory nào hữu ích nhất?

Dựa trên kết quả benchmark thực tế:

1. **Profile memory** - Mạnh nhất
   - Hoạt động tốt ở kịch bản `1`, `2`, `10`
   - Giữ được danh tính user và xử lý conflict đúng

2. **Episodic memory** - Khá tốt
   - Hữu ích ở kịch bản `3`, `9`
   - Agent tái sử dụng được bài học troubleshooting trước đó

3. **Semantic memory** - Yếu nhất
   - Kết quả không ổn định
   - Hoạt động tốt với leave-policy nhưng fail nhiều kịch bản khác

4. **Short-term memory** - Cần thiết
   - Quan trọng cho multi-turn flow
   - Nhưng không đủ nếu thiếu các loại memory khác

## 2. Memory nào nhạy cảm nhất?

**Profile memory** là nhạy cảm nhất về privacy.

Lý do:
- Lưu trực tiếp thông tin cá nhân: tên, công việc, vai trò, dị ứng, nhiệm vụ
- Thông tin sức khỏe (dị ứng) đặc biệt nhạy cảm
- Nếu retrieve sai hoặc bị leak: lộ danh tính/sức khỏe của user khác
- Lỗi khó phát hiện vì câu trả lời vẫn tự tin

## 3. Rủi ro PII/Privacy trong thiết kế hiện tại

### Profile memory
- Lưu PII dạng plain text
- Không có bước xin phép user rõ ràng
- Không có TTL/expiration policy
- Không mã hóa các trường nhạy cảm

### Episodic memory
- Có thể lưu incident nội bộ công ty
- Có thể giữ lại context troubleshooting nhạy cảm
- Không nên expose rộng rãi

### Semantic memory
- Rủi ro thấp hơn nếu chỉ chứa docs nội bộ
- Vẫn rủi ro nếu retrieve sai context cho sai user

### Short-term memory
- Rủi ro persistence thấp nhất (chỉ trong session)
- Vẫn chứa context hội thoại hiện tại, có thể leak trong prompt

## 4. Nếu user yêu cầu xóa memory, phải xóa ở đâu?

Để xóa hoàn toàn, phải xóa ở tất cả backends:

- **Profile memory**: `ProfileMemory.clear()` hoặc xóa Redis key
- **Episodic memory**: `EpisodicMemory.clear()`, xóa file JSON của user
- **Short-term memory**: `ShortTermMemory.clear()`
- **Semantic memory**: Nếu có insert docs của user, phải xóa vector entries

**Gap hiện tại:**
- Có deletion ở backend level
- Không có workflow deletion cho user
- Không có audit trail ghi lại đã xóa gì và khi nào

## 5. Hạn chế kỹ thuật quan sát được

### 5.1 Semantic retrieval không đáng tin cậy
Điểm yếu lớn nhất trong benchmark:
- Kịch bản `5`: Biết context SLA nhưng thiếu P2 resolution chính xác
- Kịch bản `6`: Không trả lời được `3-5 ngày làm việc`
- Kịch bản `7`: Hallucinate quy trình Level 4 không khớp document gốc
- Kịch bản `8`: Nhớ role đúng nhưng trả lời policy sai

**Kết luận:** Semantic memory là layer kém tin cậy nhất

### 5.2 Chất lượng long-context không ổn định
Kịch bản `10` cho thấy:
- Token budget hoạt động đúng: `1815` tokens
- Nhưng vẫn thiếu fact quan trọng: `2 ngày/tuần` remote
- Hệ thống có thể trong budget nhưng vẫn bỏ sót thông tin

### 5.3 Nhiều LLM calls làm chậm hệ thống
Mỗi turn có thể trigger:
- 1 main response call
- 1 fact extraction call
- 1 episode-save decision call

Tăng latency đáng kể, làm benchmark `10` conversations chạy chậm.

### 5.4 Over-saving tạo memory nhiễu
Hệ thống lưu quá nhiều:
- responsibilities
- current tasks
- drafted communication context

Hữu ích cho personalization nhưng tăng nguy cơ:
- Profile memory phình to
- Facts không liên quan lẫn vào câu trả lời sau
- Prompt chứa nhiều context không cần thiết

### 5.5 Rủi ro hallucination cao khi retrieval không đầy đủ
Các failure nguy hiểm nhất không phải câu trả lời trống, mà là **câu trả lời sai nhưng tự tin**.

Ví dụ:
- Kịch bản `7`: Bịa quy trình phê duyệt không có trong source
- Kịch bản `8`: Đưa hướng dẫn khẩn cấp sai

Nguy hiểm hơn câu trả lời chung chung vì trông có vẻ chính xác.

## 6. Điều gì sẽ fail đầu tiên khi scale?

1. **Latency** - Quá nhiều LLM calls tuần tự mỗi turn
2. **Semantic accuracy** - Nhiều documents tăng độ mơ hồ retrieval
3. **Episodic storage** - JSON files không phù hợp cho concurrent access
4. **Profile quality** - Nhiều facts tạo nhiễu nếu không có ranking/TTL/validation

## 7. Cần cải thiện gì tiếp theo?

Thứ tự ưu tiên:

1. **Cải thiện semantic retrieval**
   - Chunking tốt hơn
   - Grounding chặt chẽ hơn
   - Chỉ trả lời từ evidence đã retrieve

2. **Giảm LLM calls mỗi turn**
   - Gộp fact extraction và episode decisions

3. **Thêm profile hygiene**
   - TTL cho facts
   - Importance scoring
   - Confirmation cho facts nhạy cảm

4. **Thêm privacy controls**
   - Consent workflow
   - Deletion workflow
   - Audit logging

## 8. Kết luận cuối cùng

**Điểm mạnh:**
- Nhớ facts của user
- Cập nhật facts đã sửa
- Tái sử dụng bài học troubleshooting

**Điểm yếu:**
- Truy xuất policy chính xác
- Grounding vào document gốc
- Ngăn câu trả lời sai nhưng tự tin

**Đánh giá trung thực:**
- Kiến trúc memory đã có và hữu ích
- Benchmark chứng minh thành công một phần (`5/10`)
- Hệ thống vẫn là prototype, chưa sẵn sàng production
