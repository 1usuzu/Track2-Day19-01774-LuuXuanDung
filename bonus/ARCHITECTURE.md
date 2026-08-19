# Architecture Decision Record: Personal AI Memory System

- **Project:** Personal AI Assistant Memory for Vietnamese Users
- **Author:** AI Architecture Team
- **Status:** APPROVED / READY FOR SUBMISSION
- **Target Stack:** Qdrant (Episodic Memory) + Feast (User Profile & Velocity) + FastEmbed (BGE Embeddings)

---

## 1. Architecture Diagram

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                        USER INTERACTION STREAM                         │
 │ (Chat messages, Document notes, Reading events, Search queries)        │
 └───────────────────┬────────────────────────────────┬───────────────────┘
                     │                                │
      (Real-time Ingestion)                (Feature Events Logging)
                     ▼                                ▼
 ┌──────────────────────────────────────┐  ┌──────────────────────────────┐
 │       EPISODIC MEMORY ENGINE         │  │     FEAST FEATURE STORE      │
 │ • Storage: Qdrant Vector DB          │  │ • Storage: SQLite / Redis    │
 │ • Retriever 1: Dense Semantic        │  │ • User Profile (TTL = 30d)   │
 │ • Retriever 2: BM25 Sparse           │  │ • Query Velocity (TTL = 1h)  │
 │ • Filter: Payload [user_id]          │  │ • Item Popularity (TTL = 7d) │
 └───────────────────┬──────────────────┘  └──────────────┬───────────────┘
                     │ (Top-K Memories via RRF)           │ (Online Lookup < 10ms)
                     └────────────────┬───────────────────┘
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │       CONTEXT ASSEMBLER & PROMPT BUILDER        │
             │ Combines: Persona + Affinity + Velocity + Memory│
             └────────────────────────┬────────────────────────┘
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │         LLM RESPONSE GENERATION (OUTPUT)        │
             └─────────────────────────────────────────────────┘
```

---

## 2. Three Key Architecture Decisions with Explicit Trade-offs

### Quyết định 1: Chiến lược Phân đoạn (Chunking Strategy) cho Episodic Memory
* **Quyết định:** Áp dụng **Semantic Message-level Chunking với Sliding Window (256–384 tokens)**. Mỗi tin nhắn hội thoại hoặc đoạn ghi chú hoàn chỉnh được lưu kèm metadata (`user_id`, `timestamp`, `topic`).
* **So sánh & Trade-off:**
  - *Lựa chọn bị loại 1 (Fixed-size Character Chunking 500 chars):* Cắt ngang câu làm mất ngữ cảnh ngữ pháp tiếng Việt và làm sai lệch vector embedding.
  - *Lựa chọn bị loại 2 (Full-conversation Chunking):* Gộp toàn bộ đoạn chat 20-30 câu vào 1 vector làm loãng (dilution) thông tin chi tiết; khi truy vấn một ý nhỏ, vector similarity bị giảm mạnh và làm tràn Context Window của LLM.
* **Trade-off chấp nhận:** Tốn thêm ~15% dung lượng lưu trữ metadata nhưng nâng cao vượt bậc độ chính xác Precision@5 khi recall.

---

### Quyết định 2: Mô hình Dữ liệu Đặc trưng (Feature Schema Strategy)
* **Quyết định:** Sử dụng **Tabular Features kết hợp Rolling Time-window** trong Feast:
  - `user_profile_features`: `reading_speed_wpm`, `preferred_language`, `topic_affinity` (Entity = `user_id`, TTL = 30 ngày, batch refresh hàng ngày).
  - `query_velocity_features`: `queries_last_hour`, `distinct_topics_24h` (Entity = `user_id`, TTL = 1 giờ, streaming push).
* **So sánh & Trade-off:**
  - *Lựa chọn bị loại (Embedding Feature Views):* Lưu toàn bộ lịch sử người dùng dưới dạng một "User Embedding" vector 1024 chiều duy nhất trong Feature Store.
  - *Lý do loại:* User embedding là "hộp đen", rất khó giải thích và không thể trích xuất trực tiếp các quy tắc nghiệp vụ rõ ràng như *"User đọc tốc độ 250 wpm $\rightarrow$ sinh prompt tóm tắt ngắn"*.

---

### Quyết định 3: Chiến lược Tươi mới (Freshness & Materialization Strategy)
* **Quyết định:** Áp dụng **Dual-path Freshness**:
  - *Episodic Memory:* **Sub-second Real-time Ingestion** — Ngay khi user gửi ghi chú/tài liệu mới, hệ thống embed và upsert vào Qdrant ngay lập tức ($< 100$ms).
  - *User Profile & Aggregates:* **Micro-batch Materialization (5 phút / 1 giờ)** — Các thống kê tốc độ đọc, tần suất hoạt động được tổng hợp theo chu kỳ để tối ưu CPU và I/O.
* **So sánh & Trade-off:**
  - *Lựa chọn bị loại (Pure Batch Daily Sync):* Nếu user vừa dặn *"Hôm nay tôi đổi sang học Kubernetes"*, hệ thống kiểu cũ phải đợi 24h mới cập nhật profile, gây trải nghiệm "mất trí nhớ tạm thời".

---

## 3. Loại bỏ Lựa chọn Sai Lầm (Rejected Alternative)

* **Ý tưởng bị loại:** Lưu toàn bộ Episodic Memory vào Feature Store dưới dạng BLOB/String hoặc chỉ dùng 1 cơ sở dữ liệu duy nhất.
* **Lý do loại trừ dứt khoát:**
  - **Khác biệt về vòng đời (Lifecycle mismatch):** Episodic Memory tăng trưởng liên tục theo từng tin nhắn (hàng triệu bản ghi/tháng, cần tìm kiếm tương đồng vector và BM25). Trong khi Feature Store được tối ưu cho việc **Key-Value Point Lookup theo entity ID với độ trễ $< 10$ms**.
  - Việc ép một Vector Database làm Feature Store (hoặc ngược lại) sẽ làm tê liệt hiệu năng và tăng chi phí hạ tầng gấp 3–4 lần.

---

## 4. Cân nhắc Đặc thù Ngữ cảnh Tiếng Việt (Vietnamese Context)

1. **Hiện tượng Code-switching (Tiếng Việt pha thuật ngữ tiếng Anh):**
   - Kỹ sư/người dùng công nghệ Việt Nam thường xuyên gõ: *"deploy k8s cluster bị lỗi crashloopbackoff"*.
   - **Giải pháp:** Hybrid Search RRF ($k=60$) kết hợp BM25 (bắt chính xác mã lỗi `crashloopbackoff`) và Vector Embeddings đa ngữ (`bge-small` / `bge-m3` hiểu ngữ nghĩa triển khai hạ tầng).
2. **Tuân thủ Quyền riêng tư & Nghị định 13/2023/NĐ-CP:**
   - Dữ liệu memory của từng cá nhân được cô lập tuyệt đối qua **Filtered-ANN (`user_id` payload filter)**. Khi người dùng yêu cầu xóa tài khoản (Quyền được quên), hệ thống thực hiện `client.delete(filter=user_id)` đồng bộ trên cả Qdrant và Feast.

---

## 5. Giới hạn của Phiên bản PoC (Honest Limitations)

* Chưa triển khai cơ chế **Memory Decay / Consolidation** (sau 30 ngày tự động dùng LLM tóm tắt 10 cuộc hội thoại thành 1 bản tóm tắt cốt lõi).
* Hiện tại PoC chạy In-Memory Qdrant + SQLite Feast; khi lên Production quy mô lớn cần chuyển sang Qdrant Distributed Cluster + Redis Cluster.
