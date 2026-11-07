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

_Note: JSON chỉ minh họa trường `status`, không phải toàn bộ response._

## Environment Configuration — Thay đổi Gateway Port

### Mục tiêu

Thay đổi cổng truy cập Gateway từ `8080` sang `8081` thông qua `.env`, không sửa source code và không build lại image.

### 1. Chuẩn bị file `.env`

Nếu dự án chưa có `.env`:

```powershell
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Kiểm tra giá trị hiện tại:

```powershell
Get-Content .env | Select-String "^APP_PORT="
```

Kết quả:

```text
APP_PORT=8080
```

### 2. Kiểm tra cấu hình đã được Compose xử lý

```powershell
docker compose config | Select-String "published"
```

Kết quả cần thấy:

```text
published: "8080"
```

Nếu hệ thống đang chạy:

```powershell
docker compose port gateway 80
```

Kết quả:

```text
127.0.0.1:8080
```

### 3. Thay đổi port trong `.env`

Mở file:

```powershell
code .env
```

Đổi:

```env
APP_PORT=8080
```

thành:

```env
APP_PORT=8081
```

Lưu file.

### 4. Kiểm tra trên trình duyệt

```powershell
Start-Process http://localhost:8081/docs
```

Kết quả mong đợi:

- Swagger UI vẫn hoạt động.
- Gateway được truy cập qua port `8081`.
- Nginx bên trong container vẫn chạy tại port `80`.

### 5. Khôi phục sau khi demo

Đổi `.env` về:

```env
APP_PORT=8080
```

Áp dụng lại:

```powershell
docker compose up -d gateway
docker compose port gateway 80
```

Kết quả:

```text
127.0.0.1:8080
```

### Kết luận trình bày

> `APP_PORT` được tách khỏi source code và đặt trong `.env`. Nhờ đó, chúng ta thay đổi cổng triển khai mà không sửa chương trình và không build lại Docker image.
