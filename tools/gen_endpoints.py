#!/usr/bin/env python3
"""从 `reports.py` 生成 `references/endpoints.md`(15 §一 A1、§9.4 第 3 条)。

**端点表禁止手抄**:手抄的表和控制台漂了都发现不了,而 skill 装到别人机器上是一份
快照,漂了也收不回(15 §3.4)。所以这份 md 只能由本脚本从源码生成。

为什么用 ast 而不是起 app 拿 openapi:生成端点表不该要求先装一整套后端依赖 + 连上库。
ast 读的是同一份源码,少一层"生成环境和生产不一致"的可能。

用法:
    python3 tools/gen_endpoints.py                    # 默认读 ../Geo-Analytics/backend/app/reports.py
    VTAG_REPO=/path/to/Geo-Analytics python3 tools/gen_endpoints.py
    python3 tools/gen_endpoints.py --check            # 只校验已生成的文件是不是最新,不写

⚠️ `/sites` **不进对外表**(15 §3.8 第 8 条):token 已绑定单站,列站点对它既无意义,
   又与「token 不得触达 /api/sites」冲突。排除写在 EXCLUDE 里,改之前先回去改那条红线。
"""
import argparse
import ast
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("VTAG_REPO", HERE.parent.parent / "Geo-Analytics"))
SRC = REPO / "backend" / "app" / "reports.py"
OUT = HERE.parent / "vtag-geo-analytics" / "references" / "endpoints.md"
# SKILL.md 里那张摘要表也由这里生成 —— 手抄两份的下场是两份各漂各的,
# 而对面的 agent 读的恰恰是 SKILL.md 那份(15 §9.4 第 3 条)。
SKILL = HERE.parent / "vtag-geo-analytics" / "SKILL.md"
MARK_BEGIN = "<!-- BEGIN endpoints-table:由 tools/gen_endpoints.py 生成,不要手改 -->"
MARK_END = "<!-- END endpoints-table -->"

EXCLUDE = {"/sites"}

# 「用途」一列是人写的一句话(照 15 §9.2 的表),不是从代码生成的 —— 代码里没有这个信息,
# 一半的路由函数连 docstring 都没有。**契约(参数/字段)全部生成,用途只是给人读的标题。**
# **PURPOSE 优先于 docstring**:docstring 是写给我们自己看的,里面有 `_CONV_*` 这类
# 内部常量名 —— 而这个包是公开可读的,不该带公开契约之外的内部语义(15 §3.4)。
# 新加的端点没写进 PURPOSE 时才回落到 docstring:那句内部话会当场显眼,提醒补一句人话。
PURPOSE = {
    "/overview": "概览卡片(访客/会话/浏览量/事件/互动会话占比)",
    "/timeseries": "按天趋势(访客/会话/浏览量)",
    "/acquisition": "来源拆分,维度可切",
    "/pages": "页面排行",
    "/pages_timeseries": "TopN 页面按天",
    "/events": "事件名汇总",
    "/bots": "爬虫视角(常规报表已排除爬虫)",
    "/engagement": "参与度(互动会话、时长;时长看中位数)",
    "/conversions": "转化(金额按币种分组,跨币种不相加)",
    "/realtime": "近 30 分钟滚动窗",
    "/engines": "引擎侧(应答采样)× 站点侧(实测流量)并排",
    "/probe-events": "应答采样原始记录(含 answer_text 与 sources)",
    "/ivt": "无效流量报表(打标不拦截)",
    "/ivt/session-events": "单会话事件序列(抽查下钻)",
}

# 端点级的口径提醒。红线全文在 references/metrics.md 与 SKILL.md 正文,这里只放
# **读这个端点的返回值时当场会踩的那一条**。
NOTES = {
    "/engines": (
        "⚠️ 两列各讲各的事实,**不 join、不暗示因果**。`site_measurable=\"no\"` 是"
        "「跳转不留痕,技术上测不到」,**不是 0**;`probes=0` 时各率是 `null`,"
        "**也不是 0%**。"
    ),
    "/conversions": "⚠️ 金额按币种分列,**跨币种不相加**;没报币种的不默认成人民币。",
    "/acquisition": "⚠️ `key` 里的「来源未知」桶保持原样,不因为引擎侧有数据就把它归给某个引擎。",
    "/probe-events": "⚠️ 这是原始记录,**不要自己拿它算指标** —— 要算就调 `/engines`,口径在服务端的 SQL 里。",
    "/ivt": "⚠️ 数据质量账,不是安全账:打标不拦截,每条可复核到规则编号。",
}

HEAD = """<!-- 本文件由生成器从后端源码导出,不要手改;改了下次生成就冲掉。 -->

# 端点参考(共 {n} 个,对外只读)

基址 `https://geo-analytics.info/api/reports`,鉴权 `Authorization: Bearer <access_token>`。

- 日期参数一律 `from` / `to`,格式 `YYYY-MM-DD`,**北京日口径**;
- `tag_id` 全部必填,取授权时返回的那个 —— token 只绑一个站,填别的会 **403**;
- 全部是 **GET**,全部只读。这套凭证下不存在任何写操作;
- 出错:401 = token 失效或被吊销(重走授权)/ 403 = 站点对不上 / 422 = 参数不合法 /
  429 = 触发限速(看 `Retry-After`)。**任何一种失败都直接说失败,不要补一个数字上去。**

"""


# 字段注释里带的内部指代 —— 内部常量名(`_SESSION_SOURCE`)与内部文档编号(`13 §三`)——
# 对面读不懂,而且属于「公开契约之外的内部语义」,不该随公开包发出去(15 §3.4)。
# 注释本身要留(它带的是口径),去掉的只是指代。
_SCRUB = [
    (re.compile(r"[,,]?\s*(?:与|见|同源)?[^,,。;;]*[((]_[A-Z][A-Z0-9_]*[))]"), ""),
    (re.compile(r"_[A-Z][A-Z0-9_]{3,}"), ""),
    (re.compile(r"[,,]?\s*(?:可回链|见|详见)\s*\d+\s*§[^,,。;;]*"), ""),
]


def _scrub(comment):
    for pat, rep in _SCRUB:
        comment = pat.sub(rep, comment)
    return comment.strip(" ,,;;")


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def _trailing_comment(line):
    """取行尾注释。这些注释带的是口径(如「probes=0 时各率为 None」),不是装饰,
    必须一起发出去 —— 对面的 agent 不读我们的文档,只读你塞给它的这几百行(15 §3.3)。"""
    in_str = None
    for i, ch in enumerate(line):
        if in_str:
            if ch == in_str:
                in_str = None
        elif ch in "\"'":
            in_str = ch
        elif ch == "#":
            return line[i + 1:].strip()
    return ""


def _seg(src_lines, node):
    return ast.get_source_segment("\n".join(src_lines), node) or ""


def collect_models(tree, src_lines):
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(isinstance(b, ast.Name) and b.id == "BaseModel" for b in node.bases):
            continue
        fields = []
        for st in node.body:
            if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                fields.append({
                    "name": st.target.id,
                    "type": _seg(src_lines, st.annotation),
                    "comment": _scrub(_trailing_comment(src_lines[st.lineno - 1])),
                })
        out[node.name] = fields
    return out


def _kw(call, name):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _lit(node, src_lines):
    return _seg(src_lines, node) if node is not None else None


def parse_params(fn, src_lines):
    """路由函数的 query 参数。Depends 注入的(principal / db)不是参数,跳过。"""
    args = fn.args.args
    defaults = [None] * (len(args) - len(fn.args.defaults)) + list(fn.args.defaults)
    params = []
    for arg, dflt in zip(args, defaults):
        ann = _seg(src_lines, arg.annotation) if arg.annotation else ""
        if ann in ("Session", "Principal"):
            continue
        if isinstance(dflt, ast.Call) and getattr(dflt.func, "id", "") == "Depends":
            continue
        name, required, default, note = arg.arg, dflt is None, None, []
        if isinstance(dflt, ast.Call) and getattr(dflt.func, "id", "") == "Query":
            alias = _kw(dflt, "alias")
            if alias is not None:
                name = ast.literal_eval(alias)
            d = _kw(dflt, "default")
            if d is None and dflt.args:
                d = dflt.args[0]
            if d is None:
                required = True
            else:
                default = _lit(d, src_lines)
            pat = _kw(dflt, "pattern")
            if pat is not None:
                vals = ast.literal_eval(pat).strip("^$").strip("()").split("|")
                note.append("取值:" + " / ".join(vals))
            ge, le = _kw(dflt, "ge"), _kw(dflt, "le")
            if ge is not None or le is not None:
                lo = _lit(ge, src_lines) or "-"
                hi = _lit(le, src_lines) or "-"
                note.append(f"范围 {lo}~{hi}")
        elif dflt is not None:
            default = _lit(dflt, src_lines)
        params.append({
            "name": name, "type": ann, "required": required,
            "default": default, "note": ";".join(note),
        })
    return params


def render_model(name, models, depth=0, seen=None):
    seen = seen or set()
    if name not in models or name in seen:
        return []
    seen = seen | {name}
    out = []
    pad = "  " * depth
    for f in models[name]:
        c = f"    # {f['comment']}" if f["comment"] else ""
        out.append(f"{pad}{f['name']}: {f['type']}{c}")
        inner = f["type"].replace("Optional[", "").replace("list[", "").strip("]")
        if inner in models:
            out += render_model(inner, models, depth + 1, seen)
    return out


def build():
    src_lines = _lines(SRC)
    tree = ast.parse("\n".join(src_lines))
    models = collect_models(tree, src_lines)

    blocks = []
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        for dec in fn.decorator_list:
            if not (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "get"):
                continue
            path = ast.literal_eval(dec.args[0])
            if path in EXCLUDE:
                continue
            rm = _kw(dec, "response_model")
            rm_src = _seg(src_lines, rm) if rm else ""
            model = rm_src.replace("list[", "").strip("]")
            doc = (ast.get_docstring(fn) or "").strip().splitlines()
            blocks.append({
                "path": path,
                "doc": PURPOSE.get(path) or (doc[0] if doc else ""),
                "params": parse_params(fn, src_lines),
                "resp": rm_src,
                "fields": render_model(model, models),
            })

    table = ["| 端点 | 用途 | 参数(除 `tag_id`/`from`/`to`) |", "|---|---|---|"]
    for b in blocks:
        extra = [p for p in b["params"] if p["name"] not in ("tag_id", "from", "to")]
        cells = ", ".join(f"`{p['name']}`" for p in extra) or "—"
        nodate = "" if any(p["name"] == "from" for p in b["params"]) else " ⚠️**无日期参数**"
        table.append(f"| `{b['path']}` | {b['doc'] or '—'}{nodate} | {cells} |")

    md = [HEAD.format(n=len(blocks))] + table + [""]

    for b in blocks:
        md.append(f"## `GET {b['path']}`\n")
        if b["doc"]:
            md.append(b["doc"] + "\n")
        if NOTES.get(b["path"]):
            md.append(NOTES[b["path"]] + "\n")
        md.append("参数:\n")
        md.append("| 名称 | 类型 | 必填 | 默认 | 约束 |")
        md.append("|---|---|---|---|---|")
        for p in b["params"]:
            md.append(f"| `{p['name']}` | `{p['type']}` | "
                      f"{'是' if p['required'] else '否'} | "
                      f"{'`' + p['default'] + '`' if p['default'] else '—'} | "
                      f"{p['note'] or '—'} |")
        md.append(f"\n响应 `{b['resp']}`:\n")
        md.append("```")
        md += b["fields"] or ["(无字段)"]
        md.append("```\n")
    return "\n".join(md) + "\n", "\n".join(table)


def inject(table):
    """把摘要表塞回 SKILL.md 的两个标记之间。标记不在就是有人手删了 —— 直接报错,
    不猜位置:猜错的结果是 SKILL.md 里有两张表,而对面只会读到先出现的那张。"""
    txt = SKILL.read_text(encoding="utf-8")
    i, j = txt.find(MARK_BEGIN), txt.find(MARK_END)
    if i < 0 or j < 0:
        sys.exit(f"{SKILL} 里找不到 endpoints-table 标记")
    return txt[:i] + MARK_BEGIN + "\n" + table + "\n" + txt[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只比对,不写")
    a = ap.parse_args()
    if not SRC.exists():
        sys.exit(f"找不到 {SRC};用 VTAG_REPO= 指到 Geo-Analytics 仓库根目录")
    new, table = build()
    new_skill = inject(table)
    if a.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != new or SKILL.read_text(encoding="utf-8") != new_skill:
            sys.exit(f"端点表与 {SRC} 不同步 —— 跑一次 tools/gen_endpoints.py")
        print("端点表与后端同步(references/endpoints.md + SKILL.md)")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new, encoding="utf-8")
    SKILL.write_text(new_skill, encoding="utf-8")
    print(f"已写 {OUT}\n已写 {SKILL} 的端点表")


if __name__ == "__main__":
    main()
