# Stheno — Technical Repair Roadmap

**Ngày thực hiện:** 20/11/2026  
**Phạm vi:** Memory System, Retrieval Pipeline, Chat Context và Application Entry Point.

## 1. Mục tiêu

Ổn định hệ thống Stheno hiện tại trước khi phát triển thêm các tính năng mới.

Các mục tiêu chính:

- Không nhầm lẫn ký ức giữa User, Stheno và người thứ ba.
- Không để một LLM tự quyết định toàn bộ tính đúng đắn của Memory Retrieval.
- Không loại bỏ ký ức liên quan trước khi AI Reranker được tiếp cận.
- Không để Chat Model tự biến suy đoán thành ký ức cá nhân.
- Bảo đảm ứng dụng khởi chạy được thông qua entry point thống nhất.
- Có bộ kiểm thử để phát hiện những lỗi tương tự trong tương lai.

**Nguyên tắc thiết kế:**

Python chịu trách nhiệm kiểm soát dữ liệu, validation và các quy tắc có thể xác định bằng logic.

LLM chịu trách nhiệm hiểu ngôn ngữ tự nhiên, phân tích ngữ cảnh và đánh giá mức độ liên quan.

LLM không được phép tự quyết định vượt qua các ràng buộc dữ liệu do Python kiểm soát.

---

# PHASE 0 — BACKUP & BASELINE

**Ưu tiên: P0**

Trước khi chỉnh sửa source code:

1. Kiểm tra trạng thái Git bằng `git status`.
2. Kiểm tra các thay đổi chưa commit hiện có.
3. Tạo branch riêng cho quá trình sửa chữa.
4. Sao lưu `data/stheno.db`.
5. Không commit `.env`, API keys hoặc dữ liệu cá nhân ngoài ý muốn.
6. Lưu lại kết quả một số hội thoại đang hoạt động để làm baseline so sánh.

Không sử dụng `git reset --hard` hoặc ghi đè các thay đổi chưa được sao lưu.

**Điều kiện hoàn thành:**
- Có bản sao database.
- Có thể khôi phục trạng thái source code trước khi sửa.
- Không mất các thay đổi đang làm dở.

---

# PHASE 1 — XÂY DỰNG TEST & DEBUG BASELINE

**Ưu tiên: P0**

Trước khi sửa logic, cần có khả năng xác định chính xác lỗi xảy ra ở đâu.

## 1.1. Bổ sung debug cho Memory Pipeline

Theo dõi các thông tin:

- User message.
- Conversation history được truyền vào.
- Số lượng memory trong database.
- Candidate memories sau keyword ranking.
- Candidate score của từng memory.
- Subject của từng candidate.
- Target subject do Reranker trả về.
- Memory IDs do Reranker lựa chọn.
- Memory cuối cùng được Python chấp nhận.
- Memory context thực tế được gửi đến Chat Model.

Sử dụng log có cấu trúc để dễ đối chiếu giữa các bước.

Chỉ bật log nội dung hội thoại khi đang debug. Không ghi toàn bộ dữ liệu cá nhân vào log production.

## 1.2. Tạo bộ test cơ bản

Sử dụng dữ liệu cố định:

| ID | Subject | Content |
|---|---|---|
| U1 | user | Likes cats |
| U2 | user | Dislikes oily food |
| S1 | stheno | Likes dogs |
| S2 | stheno | Likes purple |
| O1 | other | Best friend likes rabbits |
| O2 | other | Mother likes roses |
| O3 | other | Younger sister studies Java |

Kiểm tra cả kết quả retrieval lẫn nội dung được đưa vào Chat Context.

**Điều kiện hoàn thành:**
- Có thể tái hiện lỗi subject selection.
- Biết chính xác memory nào được chuyển sang Chat Model.
- Có thể chạy test mà không cần gọi Ollama thật đối với các phần logic Python.

---

# PHASE 2 — FIX SUBJECT RESOLUTION

**Ưu tiên: P0 — Quan trọng nhất**

## 2.1. Sửa mâu thuẫn trong memory_retriever.txt

Rà soát toàn bộ prompt và thống nhất quy tắc:

- `user`: ký ức về người dùng Dũng.
- `stheno`: ký ức về chính Stheno.
- `other`: ký ức về người thứ ba.
- `unknown`: không xác định được chủ thể.

Quy tắc nhận diện:

| Câu hỏi | Expected subject |
|---|---|
| Anh thích con gì? | user |
| Em thích con gì? | stheno |
| Bạn thân anh thích con gì? | other |
| Mẹ anh thích hoa gì? | other |
| Em gái anh đang học gì? | other |

Đặc biệt, đại từ sở hữu không được quyết định chủ thể.

Trong câu "Bạn thân anh thích thỏ", từ "anh" chỉ xác định mối quan hệ với Dũng. Chủ thể thực sự của ký ức là bạn thân, không phải Dũng.

## 2.2. Chuyển các quy tắc rõ ràng sang Python

Bổ sung một bước xác định subject có tính xác định cho những câu diễn đạt rõ ràng.

Ví dụ:

- "Anh thích..." → user.
- "Em thích..." → stheno.
- "Bạn thân anh..." → other.
- "Mẹ anh..." → other.
- "Em gái anh..." → other.

Đây chỉ là các mẫu nhận diện rõ ràng, không phải bộ phân tích toàn bộ ngôn ngữ tiếng Việt.

Không ép phân loại nếu câu hỏi mơ hồ.

Khi không xác định chắc chắn, cho phép fallback sang LLM hoặc trả về `unknown`.

## 2.3. Thêm Subject Guard độc lập

Không để kết quả `target_subject` của Reranker trở thành nguồn kiểm soát duy nhất.

Luồng mong muốn:

`User Message`
→ `Subject Resolution`
→ `Candidate Filtering`
→ `AI Reranking`
→ `Python Validation`
→ `Selected Memories`

Khi Python đã xác định được subject từ một mẫu rõ ràng, Reranker không được phép thay đổi subject đó.

Ví dụ:

Input: "Bạn thân anh thích con gì?"

Expected:
- target_subject = other.
- Chỉ xét memory có subject = other.
- Không được trả memory của user hoặc Stheno.

Với câu hỏi mơ hồ, không ép một subject sai chỉ để có kết quả.

**Điều kiện hoàn thành:**
- Các trường hợp tường minh được phân loại bằng Python.
- AI Reranker không thể đưa memory sai subject vượt qua validation.
- Các trường hợp không xác định được chủ thể có thể trả về danh sách rỗng.

---

# PHASE 3 — FIX CANDIDATE RETRIEVAL

**Ưu tiên: P0**

## 3.1. Sửa giới hạn candidate

Hiện tại `MemoryRetriever` khai báo `max_candidates=60`, nhưng thực tế chỉ lấy:

`ranked_memories[:20]`

Sửa thành sử dụng đúng thuộc tính `self.max_candidates`.

Không hardcode giới hạn ở nhiều vị trí khác nhau.

Phân biệt rõ:

- `max_candidates`: số memory tối đa đưa cho Reranker.
- `max_retrieved`: số memory tối đa Reranker được phép chọn.

Hai thông số này không có cùng ý nghĩa.

## 3.2. Ưu tiên candidate đúng subject

Khi Subject Resolution xác định được chủ thể rõ ràng:

- Lọc candidate theo subject trước.
- Sau đó mới thực hiện keyword ranking.
- Không fallback sang subject khác chỉ vì không tìm thấy memory phù hợp.

Ví dụ:

"Bạn thân anh thích con gì?"

Không được đưa memory `user` hoặc `stheno` vào danh sách candidate cuối cùng chỉ vì chúng có điểm keyword cao hơn.

## 3.3. Đánh giá keyword ranking

Kiểm tra khả năng matching giữa:

- Tiếng Việt có dấu.
- Tiếng Việt không dấu.
- Nội dung memory tiếng Anh.
- Từ đồng nghĩa.
- Các cách diễn đạt khác nhau của cùng một ý.

Chưa cần triển khai embedding hoặc vector database trong giai đoạn này.

Trước mắt, cần xác định candidate recall có đủ tốt hay không.

**Điều kiện hoàn thành:**
- `self.max_candidates` hoạt động đúng.
- Memory đúng subject không bị loại bởi một giới hạn hardcode cũ.
- Có test kiểm tra candidate recall với database lớn hơn 20 records.

---

# PHASE 4 — FIX CHAT CONTEXT & HALLUCINATION

**Ưu tiên: P0**

## 4.1. System Prompt luôn tồn tại

Hiện tại system message chứa memory instructions chỉ được thêm khi `memories` không rỗng.

Điều này khiến trường hợp không tìm thấy memory có thể không nhận được các quy tắc grounding từ Python.

Tách thành hai phần:

**Base System Prompt:**

- Identity và personality.
- Cách xưng hô.
- Quy tắc giao tiếp.
- Phân biệt ký ức, kiến thức chung, suy luận và tưởng tượng.
- Không tự khẳng định những thông tin cá nhân chưa được xác nhận.

**Dynamic Memory Context:**

- Subject.
- Category.
- Content.
- Importance.
- Các memory được retrieval lựa chọn.

Base System Prompt phải được gửi trong mọi request, kể cả khi không có memory.

Trước khi triển khai, kiểm tra Modelfile đang thực sự được Ollama sử dụng để tránh xung đột giữa các system prompt.

## 4.2. Quy tắc sử dụng memory

Chat Model cần hiểu:

- Memory `user` là thông tin về Dũng.
- Memory `stheno` là thông tin về chính Stheno.
- Memory `other` là thông tin về người thứ ba.
- Không được chuyển ký ức giữa các chủ thể.
- Không tìm thấy memory không đồng nghĩa với việc thông tin đó chắc chắn không tồn tại.
- Không được trình bày suy đoán thành ký ức đã xác nhận.

Ví dụ:

Nếu không có memory xác nhận Stheno thích mèo, Stheno có thể nói:

"Em nghĩ mèo đen khá dễ thương."

Nhưng không được khẳng định:

"Em đã luôn thích mèo từ trước đến giờ."

trừ khi thông tin đó có cơ sở trong memory hoặc ngữ cảnh roleplay đã được xác định rõ.

## 4.3. Kiểm tra History

Đảm bảo:

- History đúng thứ tự.
- Không gửi trùng user message hiện tại.
- Assistant response cũ không tự động trở thành bằng chứng memory.
- Memory context không bị trộn lẫn với conversation history.

**Điều kiện hoàn thành:**
- System prompt luôn hiện diện.
- Subject của memory được bảo toàn.
- Các test không có memory phù hợp không tạo ra ký ức cá nhân giả.

---

# PHASE 5 — FIX APPLICATION ENTRY POINT

**Ưu tiên: P0**

Hiện tại:

- `run.ps1` gọi `python -m src.main`.
- `src/main.py` chỉ in banner.
- CLI thực tế nằm trong `src/interface/cli.py`.

Thống nhất một entry point duy nhất.

Hướng triển khai:

1. Chọn `src.main` làm entry point chính.
2. Cho `src.main` gọi CLI thực tế.
3. Cập nhật `run.ps1` để sử dụng entry point này.
4. Đồng bộ hướng dẫn khởi chạy trong README.
5. Kiểm tra cách khởi chạy bằng PowerShell từ thư mục gốc project.

Không để README và launcher sử dụng hai đường khởi chạy khác nhau.

**Điều kiện hoàn thành:**
- Chạy `.\run.ps1` mở được CLI.
- Có thể gửi message.
- Conversation được khởi tạo.
- Ollama được gọi khi cần.
- Không chỉ in banner rồi kết thúc.

---

# PHASE 6 — TEST & REGRESSION

**Ưu tiên: P0**

Bổ sung test vào thư mục `tests/`.

Ưu tiên unit test sử dụng mock/fake Ollama để không phụ thuộc kết quả ngẫu nhiên từ LLM.

Các trường hợp bắt buộc:

| Test | Input | Expected |
|---|---|---|
| T1 | Anh thích con gì? | user / U1 |
| T2 | Em thích con gì? | stheno / S1 |
| T3 | Bạn thân anh thích con gì? | other / O1 |
| T4 | Mẹ anh thích hoa gì? | other / O2 |
| T5 | Em gái anh đang học gì? | other / O3 |
| T6 | Người đó thích gì? | Resolve bằng history hoặc abstain |
| T7 | Em thích ăn món gì? | Không bịa nếu không có memory |
| T8 | Bạn thân anh học trường nào? | Không lấy O1 vì sai chủ đề |
| T9 | Reranker trả memory sai subject | Python phải loại bỏ |
| T10 | Database có trên 20 memories | Candidate limit hoạt động đúng |

Kiểm thử riêng:

- Memory Extraction.
- Subject Resolution.
- Candidate Filtering.
- Reranker Parser.
- Subject Guard.
- Context Construction.
- Conversation orchestration.

**Điều kiện hoàn thành:**
- Tất cả unit test đều pass.
- Các trường hợp lỗi trước đây có regression test.
- Test không cần gọi LLM thật vẫn xác minh được các quy tắc Python.

---

# PHASE 7 — CLEANUP & CONFIGURATION

**Ưu tiên: P1**

Sau khi các chức năng chính hoạt động:

1. Kiểm tra lại cấu hình trong `settings.json`.
2. Wire các cấu hình thực sự cần dùng.
3. Loại bỏ hoặc triển khai các cấu hình đang không có hiệu lực.
4. Thống nhất `max_retrieved`, `max_candidates`, `min_importance`.
5. Kiểm tra `enable_deduplication`.
6. Kiểm tra database path được sử dụng thực tế.
7. Bổ sung logging cho những exception đang bị che khuất bởi `return []`.

Không thay đổi database schema trong bước này.

---

# PHASE 8 — COMMIT & DOCUMENTATION

**Ưu tiên: P0**

Trước khi kết thúc:

1. Chạy toàn bộ test.
2. Kiểm tra `git diff`.
3. Kiểm tra không có thông tin nhạy cảm bị đưa vào commit.
4. Cập nhật README về kiến trúc và cách chạy.
5. Ghi lại các lỗi đã sửa và test tương ứng.
6. Commit theo từng nhóm chức năng.

Gợi ý commit:

- `test: add memory pipeline regression tests`
- `fix: enforce deterministic subject resolution`
- `fix: respect memory candidate limits`
- `fix: always provide grounded chat system context`
- `fix: launch CLI through main entry point`
- `docs: update technical repair roadmap`

---

# OUT OF SCOPE — CHƯA TRIỂN KHAI NGÀY 20/11

Để tránh mở rộng phạm vi khi nền tảng chưa ổn định, tạm thời chưa thực hiện:

- Vector database / Embedding Retrieval.
- RAG architecture mới.
- Entity ID migration cho toàn bộ third-party memories.
- Emotion Engine.
- TTS.
- Avatar.
- Giao diện chat mới.
- Refactor toàn bộ project architecture.

Các hạng mục trên sẽ được đánh giá sau khi Memory Pipeline vượt qua bộ regression test.

---

# DEFINITION OF DONE

Ngày sửa chữa được xem là hoàn thành khi:

- [ ] Có backup database và branch sửa chữa.
- [ ] Có debug log để truy vết memory pipeline.
- [ ] Subject Resolution xử lý được các câu hỏi tường minh.
- [ ] Reranker không thể đưa memory sai subject vượt qua Python validation.
- [ ] Candidate limit sử dụng đúng configuration.
- [ ] Chat System Prompt luôn được gửi.
- [ ] No-memory cases không tự tạo ra ký ức cá nhân.
- [ ] `run.ps1` khởi chạy được CLI.
- [ ] Regression tests đều pass.
- [ ] README được cập nhật.
- [ ] Các thay đổi được commit rõ ràng.

**Mục tiêu cuối cùng:**

Stheno không chỉ cần có khả năng ghi nhớ. Stheno cần biết mình đang nhớ về ai, nhớ điều gì, dữ liệu đó đến từ đâu và khi nào nên thừa nhận rằng mình không biết.