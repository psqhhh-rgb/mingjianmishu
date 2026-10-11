#!/usr/bin/env bash
# 一次性把本地分支对齐到远端（两者内容一致时无损失）。
# 用途：当推送是通过 GitHub API 完成、导致本地 HEAD 与远端 SHA 不同（内容相同）后，恢复干净状态。
set -e
cd "$(dirname "$0")/.."
echo "拉取远端..."
git -c credential.helper= fetch origin
echo "重置本地 main -> origin/main ..."
git reset --hard origin/main
echo "完成："
git log --oneline -3
