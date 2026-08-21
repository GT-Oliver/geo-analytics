#!/usr/bin/env bash
# 打出可上传的 zip —— **SKILL.md 必须在 zip 根目录**。
#
# skillhub.cn 的发布检查清单:「ZIP 包或 Skill 文件夹内必须包含 SKILL.md」,
# 步骤里更严格:「确认根目录包含 SKILL.md」。
# 在仓库根 `zip -r` 会打出 vtag-geo-analytics/SKILL.md —— 根目录没有它,当场判缺文件。
# 所以这里 cd 进包目录再打,zip 里第一层就是 SKILL.md / scripts / references。
#
# 用法: tools/pack.sh   → dist/vtag-geo-analytics-<version>.zip
set -euo pipefail
cd "$(dirname "$0")/.."
PKG=vtag-geo-analytics
ver=$(sed -n 's/^version:[[:space:]]*//p' "$PKG/SKILL.md" | head -1)
[ -n "$ver" ] || { echo "SKILL.md frontmatter 里没有 version" >&2; exit 1; }

mkdir -p dist
out="dist/${PKG}-${ver}.zip"
rm -f "$out"
( cd "$PKG" && zip -qr "../$out" . -x '.*' -x '*/.*' )

# 打完就验,不靠"我记得打对了":根目录有没有 SKILL.md、文件数与体积在不在平台限内
# (单次上传 ≤ 10.00 MB,建议 ≤ 200 个文件)。
unzip -l "$out" | awk '{print $4}' | grep -qx "SKILL.md" \
  || { echo "zip 根目录没有 SKILL.md —— 这个包传上去会被判缺文件" >&2; exit 1; }
n=$(unzip -l "$out" | tail -1 | awk '{print $2}')
sz=$(stat -c%s "$out")
[ "$sz" -le 10485760 ] || { echo "超过 10 MB 上传上限:$sz" >&2; exit 1; }
[ "$n" -le 200 ] || echo "⚠️ 文件数 $n,超过建议的 200" >&2
echo "$out  (${n} 个文件, ${sz} 字节, 根目录含 SKILL.md ✅)"
