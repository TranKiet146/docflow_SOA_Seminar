# DocFlow seminar demonstration

## Demo — Multi-container Deployment

### 1. Start DocFlow

```powershell
docker compose up -d --build
```

**Kết quả:** Gateway, API, Redis và Worker hoạt động.

Mở Swagger UI:

http://localhost:8080/docs

### 2. Stop Worker

```powershell
docker compose stop worker
```

**Kết quả:** Worker dừng, Gateway, API và Redis vẫn hoạt động.

### 3. Upload File — Swagger UI

Trong Swagger UI:

1. Chọn `POST /api/jobs`.
2. Nhấn **Try it out**.
3. Upload một file `.txt` hoặc `.md` nhỏ.
4. Nhấn **Execute**.
5. Sao chép `job_id` từ response.

**Kết quả:** API vẫn tiếp nhận file và tạo job dù Worker đã dừng.

### 4. Check Job Status — Swagger UI

1. Chọn `GET /api/jobs/{job_id}`.
2. Nhập `job_id` vừa nhận.
3. Nhấn **Execute**.

**Kết quả mong đợi:**

```json
{
  "status": "queued"
}
```

Job đang chờ trong Redis Queue vì Worker đã dừng.

### 5. Restart Worker

```powershell
docker compose start worker
```

**Kết quả:** Worker hoạt động trở lại mà không cần restart các container khác.

### 6. Check Job Status Again — Swagger UI

Gọi lại:

`GET /api/jobs/{job_id}`

**Kết quả mong đợi sau khi xử lý hoàn tất:**

```json
{
  "status": "finished"
}
```

Job được Worker lấy từ Redis Queue và xử lý thành công.

---

**Conclusion:** Multi-container cho phép Worker dừng và khởi động lại độc lập. API và Redis vẫn tiếp nhận, lưu trữ jobs trong thời gian Worker không hoạt động; khi Worker trở lại, các jobs đang chờ có thể tiếp tục được xử lý.

*Note: JSON chỉ minh họa trường `status`, không phải toàn bộ response.*