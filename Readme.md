# Geo-Analytics-Skill

对外发布的 skill 包 —— 让**别人的 agent** 把 Vtag / GEO Analytics 当数据源调:
查一个网站在 AI 引擎里的可见度(引擎侧应答采样)与 AI 来源的站点侧流量、转化。

本仓库只有一件事:把 `Geo-Analytics` 后端 `/api/reports/*` 的**十四个只读端点**
包成一份说明书发到 skill 市场。它跑在**对面的 agent 进程里**,我们不托管任何东西。

> 设计出处:`Geo-Analytics/docs/15-Agent化设计.md`(方向二,§3.2「先 skill 后 MCP」;
> 骨架在 §九)。**文档是准绳**:改这里之前先改那份文档。

## 目录

```
vtag-geo-analytics/          ← 发布出去的就是这个目录,单独一层是为了 clawhub 那条命令能直接指它
  SKILL.md                   唯一必需件:何时用 / 授权 / 端点表 / 指标 / 口径红线
  scripts/vtag.sh            可选:login 跑设备码流程 + curl 取数(凭证存 ~/.vtag/credentials)
  references/
    endpoints.md             端点契约(参数 + 响应字段)—— **生成物,不要手改**
    metrics.md               六指标公式 + 口径红线全文 + 来源分档的原值含义
tools/gen_endpoints.py       生成器:读后端 reports.py,写 references/endpoints.md
                             与 SKILL.md 里那张摘要表(留在包外,包是公开可读的)
tools/pack.sh                打 dist/*.zip:SKILL.md 落在 zip 根目录,打完自校验
```

## 端点表由生成器产出,不许手抄

```bash
python3 tools/gen_endpoints.py            # 默认读 ../Geo-Analytics/backend/app/reports.py
VTAG_REPO=/path/to/Geo-Analytics python3 tools/gen_endpoints.py
python3 tools/gen_endpoints.py --check    # 只校验同步,不写;适合发版前跑一遍
```

理由是这个形态特有的:**skill 装到别人机器上就是一份快照,我们改端点它不会跟着改**。
手抄的表漂了没人发现,而已经装了的用户会静默拿到错的参数名。所以:

- 端点、参数、响应字段**只能生成**;
- 后端**发布过的端点只加不改** —— 加参数、加响应字段可以,改字段含义、改参数名、删端点不行。
  要改就发新版本并 bump `version`,老版本继续能跑;
- 生成器会**清掉内部指代**(内部常量名、内部文档编号):这个包是公开可读的,
  不带公开契约之外的内部语义。

## 包里没有密钥

设备码流程(RFC 8628)里我们是 public client,`client_id: vtag-skill` 是公开值,
**本来就没有 secret**。token 由用户当场授权换取,存在对面。
所以「包是公开的」在这里不构成任何问题 —— 别为了「开箱即用」往包里塞任何凭证。

## 发布前的阻塞项(按顺序,少一项就别发)

装出去的东西必须当场能用。现在还不能:

1. **生产部署 `/api/oauth/*`** —— 后端代码已在 `Geo-Analytics` 仓库
   (`site_tokens.py` / `device_auth.py`,迁移 `0021` / `0022`),
   但生产 `https://geo-analytics.info/api/oauth/device_authorization` 目前 **404**,
   迁移也未 apply。**发布早于部署 = 装了就报错。**
2. **控制台授权页** —— `verification_uri` 指向 `/console/#/authorize`,那个页面还没做
   (`client/console-v2/src/views/` 下无 `Authorize.tsx`)。用户批准不了,`login` 就会一直 pending。
3. **控制台 token 管理**(列表 / 吊销 / 手工生成兜底,同屏)—— 吊销是这条路唯一的兜底,
   没有它就等于发出去收不回。
4. **LICENSE** —— `SKILL.md` frontmatter 写的是「见仓库 LICENSE」,而本仓库还没有这个文件。
   发布前补上,否则那一行是空指针。
5. **端到端对数** —— 同一个问题经 skill 查一遍、在控制台看一遍,**数必须一模一样**;
   并抽查有没有编因果、有没有在没数据时给数。

## 打包上传:SKILL.md 必须在根目录

```bash
tools/pack.sh        # → dist/vtag-geo-analytics-<version>.zip,打完自校验
```

⚠️ **zip 是构建产物,不进仓库**(`dist/` 与 `*.zip` 都在 `.gitignore` 里)。要发版就现打一个:
仓库里躺着的 zip 只会变成"和源码对不上的那一份",而上传的人分不出手里这个是不是最新的。

skillhub.cn 的发布检查清单写的是「ZIP 包或 Skill 文件夹内必须包含 `SKILL.md`」,
步骤里更严格:「确认**根目录**包含 SKILL.md」。**在仓库根 `zip -r` 会打出
`vtag-geo-analytics/SKILL.md`——根目录没有它,当场判缺文件。**
`pack.sh` 是 cd 进包目录再打的,并在打完后回头验三件事:根目录有 SKILL.md、
体积 ≤ 10 MB、文件数 ≤ 200。选「上传文件夹」时同理:选的是 `vtag-geo-analytics/`,
不是仓库根。

## 发布

### skillhub.cn(读了官方教程 + 走到上传页,**未跑完审核**)

**逐字段填什么、上传那一刻才暴露的两个坑、当前阻塞项 —— 全在主仓库的
`Geo-Analytics/docs/16-skill对外发布.md`。**(操作面单一来源:这边只放包本身,
发布怎么走跟着项目文档编号走,不在两个仓库各留一份。)

来源:`https://skillhub.cn/tutorials`(页面是 SPA,内容在 JS bundle 里,网页抓取抓不到)。

| 要求 | 我们的状态 |
|---|---|
| ZIP / 文件夹**根目录**含 `SKILL.md` | ✅ 用 `tools/pack.sh` |
| 单次上传 ≤ 10.00 MB,建议 ≤ 200 个文件 | ✅ 6 个文件 / 约 13 KB |
| Slug:仅小写字母、数字、连字符,**提交后不可改** | ✅ `vtag-geo-analytics` |
| 版本号 + 变更说明 | ✅ frontmatter `version: 0.1.0`(发布时另填变更说明) |
| 描述说清输入、输出、适用边界 | ✅ 正文有端点表、口径红线、未授权时的降级 |
| frontmatter 描述能被平台抓到 | ✅ 改成**单行双引号** —— 用 YAML 折叠块 `>-` 时平台抓到的是 `>-` 这两个字符本身 |
| 计费策略 | **免费模式**——「免费模式无需商户入驻」,所以企业认证/商户号这条线整条不走 |
| 建议补 3 个效果案例 | ⬜ 未准备(发布后可补) |
| 安全审核(AI 行为分析 + 静态规则 + 沙箱,查恶意代码与**密钥泄露**) | ✅ 包里无密钥:public client 无 secret,token 由用户当场授权换取 |

**不做 Pay Skill。** 教程里的「升级为 Pay Skill」(`#agent-pay-upgrade`)是微信 Agent Pay
X402 那条线:企业认证 → 绑微信商户号 → SkillHub 开发者密钥(RSA2048)→ 微信支付下单 →
X402 预下单签名换 `payment_code` → 响应回 `402` + `WeixinPay-Required`。
我们**整条不走**,因为对外只读调用不计费(设计文档 §3.7:那本账算的是引擎侧采样的真实外部支出,
只读查库没有对应支出,合账就说不清了;闸门是限速不是计费)。
要收费是**推翻那条决策**,得先改设计文档,不是在这里加个签名步骤。

### clawhub.ai(**未实测**)

`npm i -g clawhub` → `clawhub login` → `clawhub skill publish ./vtag-geo-analytics
--slug <slug> --version <ver>`;也支持从 GitHub 导入。以上读自官网,不是跑过。

**同一个包发两处,不各做一份**。某个市场要求改元数据格式,改的是发布脚本,不是包内容。
跑通之后回来把这两节改写成实测结果——写实测,不写设计意图。

## 改这个包时最容易做错的四件事

1. **把指标计算写进 skill。** 给的是**定义**(供解释用),不是让对面拿 `/probe-events`
   原始记录自己算。一旦算,口径就落到了我们改不动的别人机器上;
2. **把 token 写进包里做「开箱即用」。** 包是公开的,示例一律走授权流程;
3. **手抄端点表。** 见上;
4. **把「下次要重新授权」写成故障。** 在存不了文件的平台上,每会话授权一次是这个形态的
   天花板,不是配置错误。写成报错的口吻,用户会一直折腾一件不存在的问题。
