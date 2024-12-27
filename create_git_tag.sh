#!/bin/bash

# Kiểm tra nếu không có tham số đầu vào
if [ -z "$1" ]; then
    echo "Usage: $0  <tag_name>"
    exit 1
fi

# Biến chứa tên tag
TAG_NAME="$1"

# Kiểm tra nếu tag không tồn tại cục bộ
if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "Tag '$TAG_NAME' does not exist locally."
    echo "Skipping local deletion."
else
    # Xóa tag cục bộ
    echo "Deleting local tag '$TAG_NAME'..."
    git tag -d "$TAG_NAME"
fi

# Xóa tag trên remote
echo "Deleting remote tag '$TAG_NAME'..."
git push origin --delete "$TAG_NAME"

# Tạo tag mới
echo "Creating new tag '$TAG_NAME'..."
git tag -a "$TAG_NAME" -m "Recreated tag $TAG_NAME"

# Đẩy tag mới lên remote
echo "Pushing new tag '$TAG_NAME' to remote repository..."
git push origin "$TAG_NAME"

echo "Tag '$TAG_NAME' has been successfully updated!"