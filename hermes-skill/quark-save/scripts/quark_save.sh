#!/usr/bin/env bash
# 一次性转存夸克分享链接到 <默认根目录>/<分享标题>/，不重命名、不写入 tasklist
set -euo pipefail

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "用法: $(basename "$0") '<夸克分享链接>'" >&2
  exit 2
fi

SHARE_URL="$1"
SAVE_ROOT="${QUARK_SAVE_ROOT:-/Hermes转存}"
CONTAINER="${QUARK_CONTAINER:-}"

command -v docker >/dev/null 2>&1 || {
  echo "结果：失败，宿主机上没有 docker 命令，无法通过容器执行转存" >&2
  exit 3
}

if [ -z "$CONTAINER" ]; then
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'quark-auto-save'; then
    CONTAINER='quark-auto-save'
  else
    CONTAINER="$(docker ps --format '{{.Names}}	{{.Image}}' 2>/dev/null | grep -i quark | head -n1 | cut -f1 || true)"
  fi
fi

if [ -z "$CONTAINER" ]; then
  echo "结果：失败，没找到 quark-auto-save 容器，请用 QUARK_CONTAINER=<容器名> 指定。当前运行中的容器：" >&2
  docker ps --format '  {{.Names}}  ({{.Image}})' >&2
  exit 3
fi

TIMEOUT_CMD=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout ${QUARK_SAVE_TIMEOUT:-1800}"
else
  echo "提示：未找到 timeout 命令，本次执行没有超时保护" >&2
fi

set +e
$TIMEOUT_CMD docker exec -i \
  -e SHARE_URL="$SHARE_URL" \
  -e SAVE_ROOT="$SAVE_ROOT" \
  "$CONTAINER" \
  python3 - <<'PY'
import json
import os
import re
import sys

share_url = os.environ["SHARE_URL"].strip()
root = os.environ.get("SAVE_ROOT", "/Hermes转存").strip().strip("/")
cfg_path = os.environ.get("CONFIG_PATH", "./config/quark_config.json")

sys.path.insert(0, os.getcwd())
import quark_auto_save as qas


def fail(message):
    print(f"结果：失败，{message}")
    sys.exit(1)


with open(cfg_path, encoding="utf-8") as f:
    cookies = json.load(f).get("cookie") or []
if not cookies:
    fail("容器内配置里没有 cookie")
cookie = cookies[0] if isinstance(cookies, list) else cookies

if "__uid" not in cookie:
    fail("容器内的 cookie 缺少 __uid，只能签到不能转存")

account = qas.Quark(cookie, 0)
if not account.init():
    fail("容器内的 cookie 无效或已过期")

parsed = account.get_id_from_url(share_url)
if not parsed:
    fail(f"无法从链接解析出分享 ID：{share_url}")
pwd_id, passcode, pdir_fid = parsed

is_sharing, stoken = account.get_stoken(pwd_id, passcode)
if not is_sharing:
    fail(f"分享不可用：{stoken}")

# 只取一页拿分享标题，不遍历整个分享
detail = account._send_request(
    "GET",
    f"{account.BASE_URL}/1/clouddrive/share/sharepage/detail",
    params={
        "pr": "ucpro",
        "fr": "pc",
        "pwd_id": pwd_id,
        "stoken": stoken,
        "pdir_fid": pdir_fid,
        "force": "0",
        "_page": 1,
        "_size": 1,
        "_fetch_banner": 0,
        "_fetch_share": 1,
        "_fetch_total": 1,
        "_sort": "file_type:asc,updated_at:desc",
    },
).json()
if detail.get("code") != 0:
    fail(f"读取分享信息失败：{detail.get('message')}")
title = (((detail.get("data") or {}).get("share") or {}).get("title") or pwd_id).strip()
safe_title = re.sub(r'[/\\:*?"<>|\r\n\t]', "_", title).strip() or pwd_id
savepath = f"/{root}/{safe_title}"

task = {
    "taskname": title,
    "shareurl": share_url,
    "savepath": savepath,
    "pattern": "",
    "replace": "",
    "enddate": "",
    "ignore_extension": False,
    "runweek": [],
}

print(f"账号：{account.nickname}")
print(f"分享标题：{title}")
print(f"目标目录：{savepath}")
print("-" * 40)

account.update_savepath_fid([task])
saved = account.do_save_task(task)

print("-" * 40)
errors = [m.strip() for m in qas.NOTIFYS if "❌" in m]
if errors:
    fail(errors[0].splitlines()[0])
if task.get("shareurl_ban"):
    fail(task["shareurl_ban"])
if saved:
    print("结果：转存成功")
else:
    print("结果：目标目录已存在同名文件，本次未新增（未重复转存）")
PY
rc=$?
set -e

if [ "$rc" -eq 124 ]; then
  echo "结果：失败，执行超过 ${QUARK_SAVE_TIMEOUT:-1800} 秒被中断（分享文件过多或夸克接口无响应）"
fi
exit "$rc"
