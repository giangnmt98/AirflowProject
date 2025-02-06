#!/bin/bash

# === Define color codes ===
COLOR_YELLOW="\033[1;33m"  # Yellow for informational text
COLOR_RED="\033[1;31m"     # Red for errors or warnings
COLOR_GREEN="\033[1;32m"   # Green for successes or highlights
COLOR_RESET="\033[0m"      # Reset to default terminal color
COLOR_BLUE="\033[1;34m"    # Blue for notices or specific highlights
# Separator for consistent formatting
SEPARATOR="========================================"

# === Hiển thị hướng dẫn sử dụng nếu thiếu argument ===
usage() {
    echo -e "${COLOR_YELLOW}Usage:${COLOR_RESET} $0 --repo-owner <owner> --repo-url <repository_url> --token <github_token> --can-write|--push-key [--key-path <key_path>]"
    echo
    echo -e "${COLOR_GREEN}Arguments:${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}  --repo-owner${COLOR_RESET}     Tên chủ sở hữu (user hoặc tổ chức trên GitHub)."
    echo -e "${COLOR_YELLOW}  --repo-url${COLOR_RESET}       Đường dẫn URL của repository trên GitHub (HTTPS hoặc SSH)."
    echo -e "${COLOR_YELLOW}  --token${COLOR_RESET}          GitHub Personal Access Token (PAT) để gọi API."
    echo -e "${COLOR_YELLOW}  --can-write${COLOR_RESET}      (Required) Đối với Deploy Key giới hạn quyền đọc."
    echo -e "${COLOR_YELLOW}  --push-key${COLOR_RESET}       (Required) Sử dụng Deploy Key để đẩy code lên (quyền ghi)."
    echo -e "${COLOR_YELLOW}  --key-path${COLOR_RESET}       (Optional) Đường dẫn lưu Deploy Key (không chứa phần mở rộng)."
    echo -e "                   Nếu không khai báo, Deploy Key mặc định lưu tại ~/.ssh/<repo-name>."
    echo
    exit 1
}

# === Xử lý các biến — nhận giá trị từ argument ===
REPO_OWNER=""
REPO_URL=""
REPO_NAME=""
GITHUB_TOKEN=""
DEPLOY_KEY_PATH=""
CAN_WRITE=false
PUSH_KEY=false

# Phân tích từng biến truyền vào
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --repo-owner) REPO_OWNER="$2"; shift ;;
        --repo-url) REPO_URL="$2"; shift ;;
        --token) GITHUB_TOKEN="$2"; shift ;;
        --key-path) DEPLOY_KEY_PATH="$2"; shift ;;
        --can-write) CAN_WRITE="$2"; shift ;;
        --push-key) PUSH_KEY="$2"; shift ;;
        *) echo -e "${COLOR_RED}Unknown parameter:${COLOR_RESET} $1"; usage ;;
    esac
    shift
done

# === Kiểm tra các biến cần thiết ===
if [[ -z "$REPO_OWNER" || -z "$REPO_URL" || -z "$GITHUB_TOKEN" ]]; then
    echo -e "${COLOR_RED}Error:${COLOR_RESET} Missing required arguments."
    usage
fi

# Xác nhận ít nhất một trong các flag --can-write hoặc --push-key được sử dụng
if [[ "$CAN_WRITE" == false && "$PUSH_KEY" == false ]]; then
    echo -e "${COLOR_RED}Error:${COLOR_RESET} You must specify either '--can-write' or '--push-key'."
    usage
fi

# === Parse Repository Name từ URL ===
REPO_NAME=$(basename -s .git "$REPO_URL")

if [[ -z "$REPO_NAME" ]]; then
    echo -e "${COLOR_RED}Error:${COLOR_RESET} Could not extract repository name from URL: $REPO_URL"
    exit 1
fi

# Xác định đường dẫn Deploy Key mặc định nếu không truyền `--key-path`
if [[ -z "$DEPLOY_KEY_PATH" ]]; then
    DEPLOY_KEY_PATH="$HOME/.ssh/${REPO_NAME}"
fi

# === Bắt đầu tạo Deploy Key ===
echo -e "\n${COLOR_GREEN}Tạo Deploy Key tại:${COLOR_RESET} ${DEPLOY_KEY_PATH}"
ssh-keygen -t ed25519 -C "deploy-key-${REPO_NAME}" -f "${DEPLOY_KEY_PATH}" -N ""

# Đọc public key vừa được tạo
DEPLOY_KEY=$(cat "${DEPLOY_KEY_PATH}.pub")
echo -e "${COLOR_GREEN}Public Key đã được tạo:${COLOR_RESET}"
echo -e "${DEPLOY_KEY}"

# === Đẩy Deploy Key lên GitHub nếu có `--push-key` ===
if [[ "$PUSH_KEY" == True ]]; then
    echo -e "${COLOR_YELLOW}Thêm Deploy Key có quyền ghi vào GitHub repository (${REPO_OWNER}/${REPO_NAME})...${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Thêm Deploy Key (chỉ quyền đọc) vào GitHub repository (${REPO_OWNER}/${REPO_NAME})...${COLOR_RESET}"
fi

API_URL="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/keys"

# Determine READ_ONLY value based on CAN_WRITE
if [[ "$CAN_WRITE" == "True" ]]; then
    READ_ONLY="false"
else
    READ_ONLY="true"
fi
echo -e "${COLOR_GREEN}CAN_WRITE:${COLOR_RESET} $CAN_WRITE"
echo -e "${COLOR_GREEN}READ_ONLY:${COLOR_RESET} $READ_ONLY"

# Build the JSON payload
JSON_PAYLOAD=$(cat <<-EOF
{
    "title": "deploy-key-${REPO_NAME}",
    "key": "${DEPLOY_KEY}",
    "read_only": ${READ_ONLY}
}
EOF
)
echo -e "\n${COLOR_GREEN}Sending JSON Payload:${COLOR_RESET}"
echo -e "${COLOR_YELLOW}${JSON_PAYLOAD}${COLOR_RESET}"

# === Gửi yêu cầu POST để thêm Deploy Key ===
HTTP_RESPONSE=$(curl -s -o response.json -w "%{http_code}" \
    -X POST -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${JSON_PAYLOAD}" \
    "${API_URL}")

if [[ "${HTTP_RESPONSE}" -eq 201 ]]; then
    echo -e "${COLOR_GREEN}Deploy Key đã được thêm thành công vào repository ${REPO_OWNER}/${REPO_NAME}.${COLOR_RESET}"
else
    echo -e "${COLOR_RED}Đã có lỗi xảy ra trong khi thêm Deploy Key:${COLOR_RESET}"
    cat response.json
    rm response.json
    exit 1
fi
rm response.json

# === Cấu hình SSH Client ===
echo -e "\n${COLOR_GREEN}Cấu hình SSH Client để sử dụng Deploy Key...${COLOR_RESET}"
SSH_CONFIG_FILE="$HOME/.ssh/config"

# Add SSH config if not already present
if ! grep -q "${DEPLOY_KEY_PATH}" "$SSH_CONFIG_FILE" 2>/dev/null; then
    cat <<-EOF >> "$SSH_CONFIG_FILE"

Host github-${REPO_NAME}
    HostName github.com
    User git
    IdentityFile ${DEPLOY_KEY_PATH}
    IdentitiesOnly yes
EOF
fi
``
# Secure the SSH configuration file
chmod 600 "$SSH_CONFIG_FILE"
echo -e "${COLOR_GREEN}Cấu hình SSH Client hoàn tất.${COLOR_RESET}"

# Add private key to SSH Agent
echo -e "${COLOR_GREEN}Thêm Private Key vào SSH Agent...${COLOR_RESET}"
eval "$(ssh-agent -s)"
ssh-add "${DEPLOY_KEY_PATH}"

# Completion message
echo -e "${COLOR_GREEN}Deploy Key đã được thêm vào SSH Agent, có thể kiểm tra bằng lệnh 'ssh-add -l'.${COLOR_RESET}"
echo -e "${COLOR_GREEN}Bây giờ đã có thể clone hoặc pull repository của mình bằng Deploy Key!${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Thực thi lệnh sau để clone repository: git clone git@github-${REPO_NAME}:${REPO_OWNER}/${REPO_NAME}.git${COLOR_RESET}"
