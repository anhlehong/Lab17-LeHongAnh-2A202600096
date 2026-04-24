# Benchmark: Multi-Memory Agent

## Thông tin chạy

- Thời gian: `2026-04-24 13:19:33`
- Kết quả: `5/10` kịch bản đạt
- Logs: `logs/20260424-130759/`

## Phương pháp

- `no-memory`: model chỉ thấy tin nhắn hiện tại
- `with-memory`: agent dùng short-term, profile, episodic và semantic memory
- Benchmark: `10` cuộc hội thoại nhiều lượt, không phải `10` câu hỏi đơn lẻ
- Nhóm test theo rubric:
  - profile recall
  - conflict update
  - episodic recall
  - semantic retrieval
  - trim/token budget

## Bảng tổng hợp

| # | Kịch bản | Kết quả no-memory | Kết quả with-memory | Pass? |
|---|----------|-------------------|---------------------|-------|
| 1 | Profile Recall + IT Helpdesk | Quên danh tính user, không trả lời chính xác | Nhớ `Minh`, `IT Support`, trả lời đúng `https://sso.company.internal/reset` / `ext. 9000` | Pass |
| 2 | Conflict Update - Dị ứng | Không giữ được fact đã sửa | Cập nhật profile từ `sữa bò` sang `đậu nành` đúng | Pass |
| 3 | Episodic Recall - VPN Issue | Chỉ trả lời chung chung | Nhớ cách fix trước: kiểm tra Internet, restart VPN client | Pass |
| 4 | Semantic - Chính sách nghỉ phép | Trả lời HR chung chung | Truy xuất đúng: `15 ngày`, giấy bác sĩ sau `>3` ngày, remote `2 ngày/tuần` | Pass |
| 5 | Semantic - SLA P1 | Không trả lời được thời gian xử lý P2 | Nhớ context SLA nhưng thiếu P2 resolution chính xác | Fail |
| 6 | Semantic - Chính sách hoàn tiền | Không trả lời được thời gian xử lý | Không truy xuất được `3-5 ngày làm việc` | Fail |
| 7 | Semantic - Kiểm soát truy cập | Trả lời chung chung | Truy xuất topic nhưng hallucinate quy trình phê duyệt Level 4 | Fail |
| 8 | Multi-Memory - IT Admin Role | Không trả lời được quy trình truy cập tạm thời | Nhớ `Hùng` và `IT Admin` nhưng trả lời sai quy trình khẩn cấp | Fail |
| 9 | Episode Chain - Xử lý ticket | Không kết nối được kinh nghiệm P1 với P2 | Tái sử dụng bài học P1, gợi ý kiểm tra logs / restart | Pass |
| 10 | Long Context - Token Budget | Quên tên, vai trò và chính sách | Nhớ `Lan` và tóm tắt chính sách nhưng thiếu giới hạn `2 ngày/tuần` remote | Fail |

## Phân tích chi tiết

### Kịch bản đạt (5/10)

- **Profile recall + IT Helpdesk**: Profile lưu đúng `{"name": "Minh", "job": "IT Support"}`, giúp cá nhân hóa và semantic lookup
- **Conflict update - Dị ứng**: Test bắt buộc từ rubric đạt, fact cuối cùng là `đậu nành`, không phải `sữa bò` cũ
- **Episodic recall - VPN**: Agent lưu episode troubleshooting và tái sử dụng đúng
- **Semantic - Chính sách nghỉ phép**: Truy xuất tốt nhất, trả lời nhiều lượt dựa trên `hr_leave_policy.txt`
- **Episode chain - Xử lý ticket**: Episodic memory hữu ích để chuyển bài học debug sang incident mới

### Kịch bản fail (5/10)

- **Semantic - SLA P1**: Biết topic nhưng thiếu P2 resolution chính xác, lẫn vào leave-policy
- **Semantic - Hoàn tiền**: Không trả lời được `3-5 ngày làm việc`, semantic layer không ổn định
- **Semantic - Kiểm soát truy cập**: Hallucinate quy trình Level 4, không khớp document gốc
- **Multi-memory - IT Admin**: Profile recall đúng nhưng áp dụng policy sai
- **Long context - Token budget**: Budget đúng (`1815` tokens) nhưng thiếu fact `2 ngày/tuần` remote

## Độ phủ theo rubric

- Profile recall: kịch bản `1`, `8`, `10`
- Conflict update: kịch bản `2`
- Episodic recall: kịch bản `3`, `9`
- Semantic retrieval: kịch bản `4`, `5`, `6`, `7`, `8`, `10`
- Trim/token budget: kịch bản `10`

## Kết luận

- Memory stack hiệu quả một phần: profile và episodic tốt, semantic yếu nhất
- Đáp ứng yêu cầu rubric: `10` cuộc hội thoại nhiều lượt, so sánh no-memory vs with-memory
- Kết quả `5/10` cho thấy hệ thống là prototype với chất lượng retrieval chưa ổn định
