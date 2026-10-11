# -*- coding: utf-8 -*-
"""
通用推送脚本：通过 GitHub Git Data API 推送本地 HEAD（绕过被代理阻断的 github.com git 通道）。

原理（无需本地拥有远端对象，规避本地/远端历史分叉）：
  1. 取远端 main 的 commit sha 与其 tree；
  2. 递归列出远端 tree 的 path->blob_sha；
  3. 用 `git ls-tree -r HEAD` 取本地 HEAD 的 path->blob_sha（git blob 为 LF 规范化内容）；
  4. 仅上传"内容 sha 不同"的文件、删除本地已无的文件，用 base_tree 组装新 tree；
  5. 以远端 main 为父提交创建新 commit，并更新 ref。

环境变量：GH_TOKEN（必填）
用法：GH_TOKEN=xxx python api_push.py [--repo owner/name] [--branch main] [--tag TAG]
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API = "https://api.github.com"


def sh(*args, binary=False, cwd=None):
    out = subprocess.check_output(["git", "-c", "core.quotepath=false"] + list(args), cwd=cwd)
    return out if binary else out.decode("utf-8").strip()


def api(token, method, path, data=None, retries=5):
    url = API + path
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Authorization", "Bearer " + token)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            req.add_header("User-Agent", "github-api-push")
            if body:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")
            if e.code in (502, 503, 504) and attempt < retries - 1:
                time.sleep(2 + attempt * 2); continue
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {detail}")
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 + attempt * 2); continue
            raise


def local_blobs():
    """返回 {path: (mode, sha)}，仅常规文件。"""
    out = sh("ls-tree", "-r", "HEAD")
    d = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        if typ != "blob":
            continue
        d[path] = (mode, sha)
    return d


def remote_blobs(token, repo, tree_sha):
    """递归获取远端 tree 的 {完整路径: blob_sha}。使用 recursive=1，路径为完整路径。"""
    d = {}
    data = api(token, "GET", f"/repos/{repo}/git/trees/{tree_sha}?recursive=1")
    if data.get("truncated"):
        raise RuntimeError("远端 tree 结果被截断，文件过多，需分页处理")
    for ent in data.get("tree", []):
        if ent["type"] == "blob":
            d[ent["path"]] = ent["sha"]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--tag")
    a = ap.parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("缺少 GH_TOKEN 环境变量")

    # 在仓库根目录运行
    root = sh("rev-parse", "--show-toplevel")

    repo = a.repo
    if not repo:
        url = sh("remote", "get-url", "origin", cwd=root)
        m = re.search(r"github.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
        if not m:
            sys.exit("无法从 origin 解析 repo，请用 --repo owner/name")
        repo = m.group(1)

    head = sh("rev-parse", "HEAD", cwd=root)
    head_msg = sh("log", "-1", "--format=%B", head, cwd=root)

    ref = api(token, "GET", f"/repos/{repo}/git/ref/heads/{a.branch}")
    base_sha = ref["object"]["sha"]
    base_tree = api(token, "GET", f"/repos/{repo}/git/commits/{base_sha}")["tree"]["sha"]
    print(f"repo={repo} branch={a.branch} base={base_sha[:8]} head={head[:8]}")

    if base_sha == head:
        print("远端已与本地一致，无需推送。"); return

    local = local_blobs()
    remote = remote_blobs(token, repo, base_tree)

    to_upload = [p for p, (mode, sha) in local.items() if remote.get(p) != sha]
    to_delete = [p for p in remote if p not in local]
    print(f"本地文件 {len(local)}，远端文件 {len(remote)}；待上传 {len(to_upload)}，删除 {len(to_delete)}", flush=True)

    # 防误删保护：删除量异常偏大时中止（避免枚举异常导致远端被清空）
    if len(to_delete) > 200:
        sys.exit(f"中止：检测到待删除文件 {len(to_delete)} 个，疑似枚举异常，已阻止推送。")

    def upload(path):
        content = sh("cat-file", "blob", f"{head}:{path}", binary=True, cwd=root)
        blob = api(token, "POST", f"/repos/{repo}/git/blobs",
                   {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})
        mode = "100755" if local[path][0] == "100755" else "100644"
        return {"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]}

    entries = [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in to_delete]
    n = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for ent in ex.map(upload, to_upload):
            entries.append(ent); n += 1
            if n % 50 == 0:
                print(f"  已上传 {n}/{len(to_upload)}", flush=True)

    tree = api(token, "POST", f"/repos/{repo}/git/trees", {"base_tree": base_tree, "tree": entries})
    who = {"name": sh("config", "user.name", cwd=root) or "push-bot",
           "email": sh("config", "user.email", cwd=root) or "push-bot@users.noreply.github.com",
           "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    commit = api(token, "POST", f"/repos/{repo}/git/commits",
                 {"message": head_msg, "tree": tree["sha"], "parents": [base_sha],
                  "author": who, "committer": who})
    try:
        api(token, "PATCH", f"/repos/{repo}/git/refs/heads/{a.branch}", {"sha": commit["sha"], "force": False})
    except RuntimeError:
        api(token, "PATCH", f"/repos/{repo}/git/refs/heads/{a.branch}", {"sha": commit["sha"], "force": True})
    print(f"{a.branch} 更新 -> {commit['sha'][:8]}")

    if a.tag:
        try:
            api(token, "POST", f"/repos/{repo}/git/refs", {"ref": f"refs/tags/{a.tag}", "sha": commit["sha"]})
            print(f"tag {a.tag} -> {commit['sha'][:8]}")
        except RuntimeError as e:
            print(f"tag 跳过: {e}")

    print("DONE。本地与远端 SHA 可能不同（内容一致）；网络恢复后可 git fetch && git reset --hard origin/main 对齐。")


if __name__ == "__main__":
    main()
