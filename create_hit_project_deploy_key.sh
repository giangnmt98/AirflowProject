#!/bin/bash

# === Hiển thị hướng dẫn sử dụng nếu thiếu argument ===
usage() {
    echo "Usage: $0 --repo-owner <owner> --repo-name <repository> --token <github_token> --key-path <key_path> [--read-only] [--push-key]"
    echo
    echo "Arguments:"
    echo "  --repo-owner     Tên chủ sở hữu (user hoặc tổ chức trên GitHub)."
    echo "  --repo-name      Tên repository trên GitHub."
    echo "  --token          GitHub Personal Access Token (PAT) để gọi API."
    echo "  --key-path       Đường dẫn lưu Deploy Key (không chứa phần mở rộng)."
    echo "  --read-only      Tùy chọn. Nếu khai báo, Deploy Key chỉ có quyền đọc."
    echo "  --push-key       Tùy chọn. Nếu khai báo, Deploy Key sẽ được đẩy lên GitHub qua API."
    echo
    exit 1
}

# === Xử lý các biến — nhận giá trị từ argument ===
REPO_OWNER=""
REPO_NAME=""
GITHUB_TOKEN=""
DEPLOY_KEY_PATH=""
READ_ONLY=false
PUSH_KEY=false

# Phân tích các biến truyền vào
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --repo-owner) REPO_OWNER="$2"; shift ;;
        --repo-name) REPO_NAME="$2"; shift ;;
        --token) GITHUB_TOKEN="$2"; shift ;;
        --key-path) DEPLOY_KEY_PATH="$2"; shift ;;
        --read-only) READ_ONLY=true ;;
        --push-key) PUSH_KEY=true ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

# === Kiểm tra các biến cần thiết ===
if [[ -z "$REPO_OWNER" || -z "$REPO_NAME" || -z "$GITHUB_TOKEN" || -z "$DEPLOY_KEY_PATH" ]]; then
    echo "Error: Missing required arguments."
    usage
fi

# === Bắt đầu tạo Deploy Key ===
echo "Tạo Deploy Key tại: ${DEPLOY_KEY_PATH}"
ssh-keygen -t rsa -b 4096 -C "deploy-key" -f "${DEPLOY_KEY_PATH}" -N ""

# Đọc public key vừa được tạo
DEPLOY_KEY=$(cat "${DEPLOY_KEY_PATH}.pub")
echo "Public Key đã được tạo:"
echo "${DEPLOY_KEY}"

# === Đẩy Deploy Key lên GitHub nếu có `--push-key` ===
if [[ "$PUSH_KEY" == true ]]; then
    echo "Thêm Deploy Key vào GitHub repository (${REPO_OWNER}/${REPO_NAME})..."
    API_URL="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/keys"
    JSON_PAYLOAD=$(cat <<-EOF
    {
        "title": "deploy-key",
        "key": "${DEPLOY_KEY}",
        "read_only": ${READ_ONLY}
    }
EOF
    )

    # Gửi yêu cầu POST để thêm Deploy Key
    HTTP_RESPONSE=$(curl -s -o response.json -w "%{http_code}" \
        -X POST -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${JSON_PAYLOAD}" \
        "${API_URL}")

    if [[ "${HTTP_RESPONSE}" -eq 201 ]]; then
        echo "Deploy Key đã được thêm thành công vào repository ${REPO_OWNER}/${REPO_NAME}."
    else
        echo "Đã có lỗi xảy ra trong khi thêm Deploy Key:"
        cat response.json
        rm response.json
        exit 1
    fi
    rm response.json
else
    echo "Bỏ qua bước đẩy Deploy Key lên GitHub (do không sử dụng cờ --push-key)."
fi

# === Cấu hình SSH Client ===
echo "Cấu hình SSH Client để sử dụng Deploy Key..."
SSH_CONFIG_FILE="$HOME/.ssh/config"

cat <<-EOF >> "$SSH_CONFIG_FILE"

Host github.com
    HostName github.com
    User git
    IdentityFile ${DEPLOY_KEY_PATH}
    IdentitiesOnly yes
EOF

# Bảo vệ quyền của file cấu hình SSH
chmod 600 "$SSH_CONFIG_FILE"
echo "Cấu hình SSH Client hoàn tất."

# Thêm private key vào SSH Agent
echo "Thêm Private Key vào SSH Agent..."
eval "$(ssh-agent -s)"
ssh-add "${DEPLOY_KEY_PATH}"

# Hoàn tất
echo "Deploy Key đã được thêm vào SSH Agent. Bạn có thể kiểm tra bằng lệnh 'ssh-add -l'."
echo "Bây giờ bạn có thể clone hoặc pull repository của mình bằng Deploy Key."