
# Hướng Dẫn Sử Dụng Nhiều Deploy Key Cho Nhiều Project Git

## 1. Tạo Custom SSH Key cho Mỗi Project
Để quản lý deploy key cho nhiều dự án, cần tạo riêng một SSH key cho từng dự án. Thực hiện các lệnh sau cho mỗi project.

### Lệnh Tạo SSH Key:
```bash
ssh-keygen -t ed25519 -C "deploy-key-for-project-a" -f ~/.ssh/project_a_key
ssh-keygen -t ed25519 -C "deploy-key-for-project-b" -f ~/.ssh/project_b_key
```

- **`-C`**: Ghi chú để nhận diện key.
- **`-f`**: Chỉ định đường dẫn và tên file của key.

Sau khi thực hiện, mỗi lệnh sẽ tạo ra 2 file:
- Khóa riêng tư: `~/.ssh/project_a_key` và `~/.ssh/project_b_key`
- Khóa công khai: `~/.ssh/project_a_key.pub` và `~/.ssh/project_b_key.pub`

---

## 2. Thêm SSH Key vào GitHub như Deploy Key
1. **Mở file khóa công khai**:
   ```bash
   cat ~/.ssh/project_a_key.pub
   ```

2. **Truy cập GitHub**:
   - Vào repository muốn thêm deploy key (Project A hoặc B).
   - **Settings** > **Deploy keys** > **Add deploy key**.
   - **Dán nội dung** của file khóa công khai vào ô **Key**.
   - Đặt tên cho key, ví dụ: "Project A Deploy Key".
   - (Tùy chọn) Tick vào **Allow write access** nếu cần quyền ghi.

3. Lặp lại quá trình cho từng repository với từng SSH key tương ứng.

---

## 3. Cấu hình Nhiều Host trong SSH Config
Tạo hoặc mở file SSH config:

```bash
nano ~/.ssh/config
```

Thêm cấu hình cho từng project như sau:

```bash
# Cấu hình cho Project A
Host github-project-a
    HostName github.com
    User git
    IdentityFile ~/.ssh/project_a_key
    IdentitiesOnly yes

# Cấu hình cho Project B
Host github-project-b
    HostName github.com
    User git
    IdentityFile ~/.ssh/project_b_key
    IdentitiesOnly yes
```

- **`Host`**: Tạo alias cho từng project.
- **`IdentityFile`**: Chỉ định file SSH key tương ứng với mỗi repository.
- **`IdentitiesOnly yes`**: Đảm bảo SSH chỉ dùng key trong cấu hình.

---

## 4. Kiểm Tra Kết Nối SSH cho Từng Host
Chạy lệnh sau để đảm bảo mỗi host được kết nối đúng:

```bash
ssh -T git@github-project-a
ssh -T git@github-project-b
```

Nếu thấy thông báo sau thì có nghĩa kết nối đã thành công:

```
Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## 5. Clone Repository Sử Dụng Host Đã Cấu Hình
Sử dụng alias host đã thiết lập trong SSH config để clone các repository:

- **Clone Project A**:
  ```bash
  git clone git@github-project-a:username/project-a.git
  ```

- **Clone Project B**:
  ```bash
  git clone git@github-project-b:username/project-b.git
  ```

---
