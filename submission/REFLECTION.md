# Reflection — Lab 19

**Tên:** Lưu Xuân Dũng
**Cohort:** 3B
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Qua thực nghiệm trên 50 câu hỏi golden set:

- **`exact` thắng vì nó dựa trên từ khóa để khớp chuỗi ký tự trực tiếp, không bị nhiễu ngữ nghĩa. Cụ thể là dùng BM25
- **`paraphrase` thắng nhờ khả năng hiểu ngữ cảnh không gian vector dù không chứa từ khóa gốc. Cụ thể là dùng Vector Search
- **`mixed` thắng hoàn toàn và đạt precision trung bình cao nhất vì tận dụng ưu điểm của cả hai. Cụ thể là dùng Hybrid Search

**Khi nào KHÔNG dùng Hybrid:**

- Dùng Pure BM25 khi: Tra cứu mã lỗi, log trace, số hóa đơn, SKU hàng hóa (yêu cầu khớp 100%), hoặc khi hệ thống bị giới hạn tài nguyên không thể gánh thêm chi phí/latency của embedding model.
- Dùng Pure Vector khi: Tìm kiếm dữ liệu đa phương thức (hình ảnh, video) hoặc tìm kiếm đa ngôn ngữ (cross-lingual) không có từ khóa trùng lặp.

---

## Điều ngạc nhiên nhất khi làm lab này

Vector Search thực sự hiểu nghĩa câu hỏi dù không có từ khóa nào trùng nhau: câu hỏi 'mở rộng hạ tầng' hoàn toàn không có chữ 'cloud' nhưng hệ thống vẫn tìm ra chính xác các bài viết về Cloud.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: không có
