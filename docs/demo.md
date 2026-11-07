# DocFlow Seminar Demonstration

> Chạy các lệnh tại thư mục gốc của dự án. Port mặc định của Gateway là `8080`.

## I. Docker Multi-Container

### 1. Khởi động hệ thống

**Thực hiện:**

```powershell
docker compose up -d --build
docker compose ps
```

**Kết quả:**

```text
gateway   healthy
api       healthy
redis     healthy
worker    Up
```

**Giải thích:** Docker Compose build image, tạo network, volume và khởi động bốn container của DocFlow.

Mở Swagger UI:

```powershell
Start-Process http://localhost:8080/docs
```

### 2. Dừng Worker

**Thực hiện:**

```powershell
docker compose stop worker
docker compose ps -a
```

**Kết quả:**

```text
worker    Exited
gateway   healthy
api       healthy
redis     healthy
```

**Giải thích:** Worker dừng độc lập; Gateway, API và Redis vẫn tiếp tục hoạt động.

### 3. Tạo Job khi Worker đã dừng

**Thực hiện trên Swagger UI:**

1. Mở `POST /api/jobs`.
2. Chọn **Try it out**.
3. Chọn file `.txt` hoặc `.md`.
4. Chọn **Execute**.
5. Sao chép `job_id` từ response.

**Kết quả:**

```json
{
  "job_id": "example-job-id",
  "status": "queued"
}
```

**Giải thích:** API vẫn tiếp nhận file và đưa job vào Redis Queue dù Worker không hoạt động.

### 4. Kiểm tra trạng thái Job

**Thực hiện trên Swagger UI:**

1. Mở `GET /api/jobs/{job_id}`.
2. Nhập `job_id`.
3. Chọn **Execute**.

**Kết quả:**

```json
{
  "status": "queued"
}
```

**Giải thích:** Job vẫn được Redis lưu trong hàng đợi và đang chờ Worker xử lý.

### 5. Khởi động lại Worker

**Thực hiện:**

```powershell
docker compose start worker
docker compose ps worker
```

**Kết quả:**

```text
worker    Up
```

**Giải thích:** Worker hoạt động trở lại mà không cần restart Gateway, API hoặc Redis.

### 6. Kiểm tra lại trạng thái Job

**Thực hiện trên Swagger UI:**

```text
GET /api/jobs/{job_id}
```

**Kết quả sau khi xử lý hoàn tất:**

```json
{
  "status": "finished"
}
```

**Giải thích:** Worker lấy job đang chờ từ Redis Queue, xử lý file và cập nhật trạng thái thành `finished`.

> JSON chỉ minh họa các trường quan trọng, không phải toàn bộ response.

---

## II. Docker Environment Configuration

### 1. Chuẩn bị file `.env`

**Thực hiện:**

```powershell
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}

Get-Content .env | Select-String "^APP_PORT="
```

**Kết quả:**

```text
APP_PORT=8080
```

**Giải thích:** `.env` chứa giá trị cấu hình có thể thay đổi mà không cần sửa source code.

### 2. Kiểm tra cấu hình hiện tại

**Thực hiện:**

```powershell
docker compose config | Select-String "published"
docker compose port gateway 80
```

**Kết quả:**

```text
published: "8080"
127.0.0.1:8080
```

**Giải thích:** Compose đã thay `${APP_PORT:-8080}` bằng giá trị `8080` và ánh xạ host port này đến port `80` của Gateway.

### 3. Thay đổi `APP_PORT`

**Thực hiện:**

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

**Kết quả:**

```text
APP_PORT=8081
```

**Giải thích:** Chỉ giá trị cấu hình triển khai thay đổi; source code và Docker image không thay đổi.

### 4. Kiểm tra Variable Interpolation

**Thực hiện:**

```powershell
docker compose config | Select-String "published"
```

**Kết quả:**

```text
published: "8081"
```

**Giải thích:** Docker Compose đã đọc giá trị mới từ `.env` và tạo Compose Configuration cuối cùng với port `8081`.

### 5. Áp dụng cấu hình mới

**Thực hiện:**

```powershell
docker compose up -d gateway
docker compose port gateway 80
```

**Kết quả:**

```text
127.0.0.1:8081
```

**Giải thích:** Compose tạo lại Gateway container với port mapping mới. Không cần `--build` vì không thay đổi source code hoặc Dockerfile.

> Không sử dụng `docker compose restart gateway` vì `restart` không tạo lại container với cấu hình port mới.

### 6. Kiểm tra trên trình duyệt

**Thực hiện:**

```powershell
Start-Process http://localhost:8081/docs
```

**Kết quả:**

- Swagger UI vẫn hoạt động.
- Gateway được truy cập qua host port `8081`.
- Nginx bên trong container vẫn chạy tại port `80`.

**Giải thích:** `.env` chỉ thay đổi host port; chương trình Nginx bên trong container không cần thay đổi.

### 7. Khôi phục port mặc định

**Thực hiện:**

Đổi `.env` về:

```env
APP_PORT=8080
```

Áp dụng lại:

```powershell
docker compose up -d gateway
docker compose port gateway 80
```

**Kết quả:**

```text
127.0.0.1:8080
```

**Giải thích:** Gateway trở lại port mặc định để tiếp tục các phần demo sau.

---

## III. Docker Network

### 1. Kiểm tra trạng thái các Service

**Thực hiện:**

```powershell
docker compose ps
```

**Kết quả:**

```text
gateway   healthy
api       healthy
redis     healthy
worker    Up
```

**Giải thích:** Các container đã tham gia những Docker Network được khai báo trong `compose.yaml`.

### 2. Kiểm tra Browser kết nối Gateway

**Thực hiện:**

```powershell
Start-Process http://localhost:8080
```

**Kết quả:** Giao diện DocFlow được hiển thị.

**Giải thích:** Browser truy cập Gateway qua port `8080`. API và Redis không publish port trực tiếp ra máy host.

```text
Browser → localhost:8080 → Gateway
```

### 3. Kiểm tra Gateway kết nối API

**Thực hiện:**

```powershell
Start-Process http://localhost:8080/docs
```

Trong Swagger UI:

1. Mở `GET /api/info`.
2. Chọn **Try it out**.
3. Chọn **Execute**.

**Kết quả:**

```json
{
  "service": "docflow-api",
  "version": "0.5.0",
  "runtime": "Python / FastAPI",
  "redis_url": "redis://redis:6379/0",
  "queue": "document-jobs"
}
```

**Giải thích:** Gateway tìm thấy service `api` bằng Docker DNS vì Gateway và API cùng tham gia `edge-net`.

```text
Browser → Gateway → api:8000
```

### 4. Kiểm tra API kết nối Redis

**Thực hiện trên Swagger UI:**

1. Mở `GET /health/ready`.
2. Chọn **Try it out**.
3. Chọn **Execute**.

**Kết quả:**

```json
{
  "status": "ready",
  "service": "docflow-api",
  "dependencies": {
    "redis": "ok"
  }
}
```

**Giải thích:** API đã phân giải service name `redis` và kết nối thành công đến `redis:6379` qua `job-net`.

```text
Browser → Gateway → API → Redis
```

---

## IV. Docker Network Isolation

### 1. Kiểm tra Gateway không tìm thấy Redis

**Thực hiện:**

```powershell
docker compose exec gateway getent hosts redis
```

**Kết quả:**

```text
Không trả về địa chỉ IP
```

**Giải thích:** Gateway chỉ tham gia `edge-net`, trong khi Redis chỉ tham gia `job-net`. Vì vậy Gateway không thể phân giải trực tiếp service name `redis`.

### 2. Kiểm tra Gateway tìm thấy API

**Thực hiện:**

```powershell
docker compose exec gateway wget -qO- http://api:8000/api/info
```

**Kết quả:** API trả về JSON thông tin service.

```json
{
  "service": "docflow-api",
  "version": "0.5.0"
}
```

**Giải thích:** Gateway và API cùng tham gia `edge-net`, nên Gateway có thể gọi API bằng địa chỉ `api:8000`.

### 3. Kiểm tra API tìm thấy Redis

**Thực hiện:**

```powershell
docker compose exec api python -c "import socket; print(socket.gethostbyname('redis'))"
```

**Kết quả ví dụ:**

```text
172.20.0.2
```

**Giải thích:** Docker DNS chuyển service name `redis` thành IP hiện tại của Redis container trên `job-net`. IP có thể thay đổi khi container được tạo lại.

---

## V. Nginx Reverse Proxy

### 1. Kiểm tra Gateway và API

**Thực hiện:**

```powershell
docker compose ps gateway api
```

**Kết quả:**

```text
gateway   healthy
api       healthy
```

**Giải thích:** Gateway và API đã sẵn sàng để thực hiện luồng Reverse Proxy.

### 2. Gửi Request qua Swagger UI

**Thực hiện:**

```powershell
Start-Process http://localhost:8080/docs
```

Trong Swagger UI:

1. Mở `GET /api/info`.
2. Chọn **Try it out**.
3. Chọn **Execute**.

**Kết quả:**

```json
{
  "service": "docflow-api",
  "version": "0.5.0",
  "runtime": "Python / FastAPI",
  "redis_url": "redis://redis:6379/0",
  "queue": "document-jobs"
}
```

**Giải thích:** Browser gửi request đến Gateway. Nginx chuyển request `/api/info` đến FastAPI tại `api:8000`.

```text
Browser
→ localhost:8080
→ Nginx Gateway
→ location /api/
→ proxy_pass http://api:8000
→ FastAPI
```

### 3. Kiểm tra HTTP Response

**Thực hiện:**

```powershell
curl.exe -i http://localhost:8080/api/info
```

**Kết quả:**

```text
HTTP/1.1 200 OK
Server: nginx
Content-Type: application/json
```

Phía dưới header là JSON do FastAPI trả về.

**Giải thích:** `Server: nginx` cho thấy request đi qua Nginx; nội dung JSON được FastAPI xử lý và trả lại thông qua Gateway.

### 4. Kiểm tra Container Logs

**Thực hiện:**

```powershell
docker compose logs --tail=30 gateway api
```

**Kết quả cần quan sát:**

```text
gateway  | GET /api/info ...
api      | GET /api/info ...
```

**Giải thích:** Gateway log cho thấy Nginx đã nhận request. API log cho thấy FastAPI đã nhận và xử lý request được Nginx chuyển tiếp.

```text
Client → Gateway nhận request → API xử lý request → Gateway trả response
```
