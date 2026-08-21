#!/usr/bin/env bash
# 打出可上传的 zip —— **SKILL.md 必须在 zip 根目录**。
#
# skillhub.cn 的发布检查清单:「ZIP 包或 Skill 文件夹内必须包含 SKILL.md」,
# 步骤里更严格:「确认根目录包含 SKILL.md」。
# 在仓库根 `zip -r` 会打出 vtag-geo-analytics/SKILL.md —— 根目录没有它,当场判缺文件。
# 所以这里 cd 进包目录再打,zip 里第一层就是 SKILL.md / scripts / references。
#
# ⚠️ 产物**打到仓库外面**(默认 $TMPDIR/vtag-skill-dist,可用 VTAG_DIST= 指定)。
#    不是"打进 dist/ 再 .gitignore 掉" —— 那样仓库目录里始终躺着一个 zip,
#    传的人分不出手里这个是不是最新的,git 忽略它也拦不住有人把它拖进上传框。
#
# 用法: tools/pack.sh           → $TMPDIR/vtag-skill-dist/vtag-geo-analytics-<version>.zip
#       VTAG_DIST=~/x tools/pack.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PKG=vtag-geo-analytics
ver=$(sed -n 's/^version:[[:space:]]*//p' "$PKG/SKILL.md" | head -1)
[ -n "$ver" ] || { echo "SKILL.md frontmatter 里没有 version" >&2; exit 1; }

OUT_DIR="${VTAG_DIST:-${TMPDIR:-/tmp}/vtag-skill-dist}"
case "$OUT_DIR" in
  "$PWD"|"$PWD"/*) echo "VTAG_DIST 指到了仓库里($OUT_DIR)—— 产物不进仓库" >&2; exit 1 ;;
esac
# 描述在两处出现:SKILL.md 的 frontmatter(平台自动抓的那份)与 docs/发布清单.md 里
# 供手填复制的那段。**抄件漂了没人会发现** —— 除非每次打包都比一遍,所以在这里比。
python3 - "$PKG/SKILL.md" docs/发布清单.md <<'PY' || exit 1
import re, sys
skill, doc = (open(p, encoding="utf-8").read() for p in sys.argv[1:3])
a = [l for l in skill.splitlines() if l.startswith("description:")]
if not a:
    sys.exit("SKILL.md 里没有 description")
a = a[0].split(":", 1)[1].strip().strip('"')
m = re.search(r"<!-- BEGIN description.*?-->\s*```\s*(.*?)\s*```\s*<!-- END description -->",
              doc, re.S)
if not m:
    sys.exit("docs/发布清单.md 里找不到 description 标记块")
if m.group(1).strip() != a:
    sys.exit("SKILL.md 与 docs/发布清单.md 的描述不一致 —— 改 SKILL.md 那份,再同步文档")
PY

mkdir -p "$OUT_DIR"
out="$OUT_DIR/${PKG}-${ver}.zip"
rm -f "$out"
( cd "$PKG" && zip -qr "$out" . -x '.*' -x '*/.*' )

# 打完就验,不靠"我记得打对了":根目录有没有 SKILL.md、文件数与体积在不在平台限内
# (单次上传 ≤ 10.00 MB,建议 ≤ 200 个文件)。
unzip -l "$out" | awk '{print $4}' | grep -qx "SKILL.md" \
  || { echo "zip 根目录没有 SKILL.md —— 这个包传上去会被判缺文件" >&2; exit 1; }
n=$(unzip -l "$out" | tail -1 | awk '{print $2}')
sz=$(stat -c%s "$out")
[ "$sz" -le 10485760 ] || { echo "超过 10 MB 上传上限:$sz" >&2; exit 1; }
[ "$n" -le 200 ] || echo "⚠️ 文件数 $n,超过建议的 200" >&2
echo "$out  (${n} 个文件, ${sz} 字节, 根目录含 SKILL.md ✅)"
