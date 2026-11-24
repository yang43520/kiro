#!/usr/bin/env python3
"""检查一个动画任务是否符合“进阶版动画创意”（animation-brief-advanced）规则。

进阶版 1.0（考点说明写了“**规范版本**：进阶版 1.0”）在 3.4 的全部检查之上，还检查：
视觉基调（光比、焦距、运镜速度、AgX 观感是否在基调范围内）、关键机位（逐行带标签的文字；坐标、对焦距离、
按 36 毫米传感器重新投影主体位置）、海报帧、渲染设置、色值和光强、明暗分区、效果优先级和“退一步”做法，
以及 rubric 的“海报帧与视觉基调”关键项。


3.x 格式（默认）：主文件 <标题>.md（含“## 场景和主体”等五节），同时核对 <标题>考点说明.md 和 rubric.json；
3.3 起还按主类目检查制作底线、专业术语、推荐插件、材质做法和重模拟数量；
3.4 起（考点说明写了“**规范版本**：3.4”）还检查动态总表、还原数值、光线色温光比、每段构图、配色和色彩脚本、三级细节和微细节，
并要求 rubric 有“动态密度”“电影级画面”“细节精致度”三个关键项。
2.x 格式：主文件 <标题>.md（含“## Prompt 与剧本”），同时核对 <标题>剧本.md 和 <标题>考点说明.md。
1.x 格式：<标题>_制作需求.md 和对应剧本。

用法：python3 check_brief.py <任务文件夹>/<标题>.md [--taxonomy 路径]
      python3 check_brief.py <任务文件夹>/<标题>_制作需求.md [--taxonomy 路径]
退出码：有 ERROR 时为 1，否则为 0。
"""
import os
import re
import sys

ERR, WARN = [], []
def err(m): ERR.append(m)
def warn(m): WARN.append(m)

HERE = os.path.dirname(os.path.abspath(__file__))
SINGLE = {"视觉造型", "渲染风格", "动态节奏", "灯光氛围", "背景环境", "色彩基调", "时序结构", "复杂度等级"}
REQUIRED = {"视觉造型", "材质质感", "渲染风格", "动态节奏", "动画行为", "灯光氛围", "背景环境", "时序结构", "复杂度等级"}
ALL_GROUPS = REQUIRED | {"色彩基调", "应用场景"}
MAIN_OK = {"位移与运动", "结构与装配", "形变与生长", "物理与特效"}


def read(path):
    raw = open(path, "rb").read()
    if not raw.startswith(b"\xef\xbb\xbf"):
        err(f"{os.path.basename(path)} 不是 UTF-8 带 BOM")
    return raw.decode("utf-8-sig")


def find_up(start, rel):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, rel)
        if os.path.exists(p):
            return p
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


def table_rows(text):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or re.match(r"^\|\s*-{2,}", s):
            continue
        rows.append([c.strip() for c in s.strip("|").split("|")])
    return rows


def load_taxonomy(path):
    t = open(path, encoding="utf-8-sig").read()
    cats = set()
    sec2 = t.split("## 二、")[1].split("## 三、")[0] if "## 二、" in t else ""
    for r in table_rows(sec2):
        if len(r) >= 6 and r[5].count("/") == 2:
            cats.add(r[5])
    tags, behaviors = {}, set()
    sec3 = t.split("## 三、")[1].split("## 四、")[0] if "## 三、" in t else ""
    for block in re.split(r"\n### ", sec3)[1:]:
        head = block.splitlines()[0]
        name = re.sub(r"^[\d.]+\s*", "", head).strip()
        rows = table_rows(block)[1:]
        if name == "动画行为":
            for r in rows:
                if len(r) >= 3:
                    behaviors.add((r[0], r[1], r[2]))
        else:
            tags[name] = {r[0] for r in rows if r}
    return cats, tags, behaviors


def recipe_ok(tier, grades):
    n = {g: grades.count(g) for g in ("L1", "L2", "L3", "L4")}
    desc = " + ".join(f"{v}×{k}" for k, v in n.items() if v)
    if tier == "基准档":
        if n["L3"] or n["L4"]:
            return False, f"基准档不能有 L3/L4（现在是 {desc}）"
        if n["L2"] == 1 and n["L1"] <= 1:
            return True, ""
        if n["L2"] == 0 and 2 <= n["L1"] <= 3:
            return True, ""
        return False, f"基准档只能是单个 L2（最多附带 1 个 L1）或 2～3 个 L1（现在是 {desc}）"
    if tier == "进阶档":
        if n["L4"]:
            return False, f"进阶档不能有 L4（现在是 {desc}）"
        core = (n["L3"] == 1 and n["L2"] == 0) or (n["L3"] == 0 and n["L2"] == 2)
        if core and n["L1"] <= 2:
            return True, ""
        return False, f"进阶档只能是单个 L3 或 L2 + L2，最多附带 2 个 L1（现在是 {desc}）"
    if n["L1"] > 2:
        return False, f"上限档最多附带 2 个 L1（现在是 {desc}）"
    if n["L4"] == 1 and n["L3"] == 0 and n["L2"] <= 1:
        return True, ""
    if n["L4"] == 0 and n["L3"] == 1 and 1 <= n["L2"] <= 2:
        return True, ""
    if n["L4"] == 0 and n["L3"] == 2 and n["L2"] == 0:
        return True, ""
    return False, f"上限档只能是单个 L4（最多附带 1 个 L2）、L3 + L2（可再加 1 个 L2）或 L3 + L3（现在是 {desc}）"


def section(text, start, end=None):
    if start not in text:
        return ""
    s = text.split(start, 1)[1]
    if end and end in s:
        s = s.split(end, 1)[0]
    return s



TOPIC_H = "## Prompt 与剧本"
TP_H = "## 考点"


def check_tp_section(sec, tp_path):
    tp = {}
    for r in table_rows(section(open(tp_path, encoding="utf-8-sig").read(), "## 考点表", "## 档位配方")):
        if len(r) >= 4 and r[0].isdigit():
            tp[r[0]] = (r[2], r[3])
    trs = [r for r in table_rows(sec) if r and r[0].isdigit()]
    if not trs:
        err("「考点」里没有考点")
    grades, ids = [], []
    for r in trs:
        if len(r) < 5:
            err(f"考点行应有 5 列：{r}"); continue
        if r[0] not in tp:
            err(f"考点编号 {r[0]} 不在考点表中"); continue
        name, g = tp[r[0]]
        if r[1] != name:
            err(f"考点 {r[0]} 的名称应为“{name}”，现在是“{r[1]}”")
        if r[2] != g:
            err(f"考点 {r[0]} 的分级应为 {g}，现在是 {r[2]}")
        grades.append(g); ids.append(r[0])
    mt = re.search(r"\*\*题目档位\*\*[：:]\s*(基准档|进阶档|上限档)", sec)
    if not mt:
        err("缺少“题目档位”（基准档/进阶档/上限档）")
    elif grades:
        ok, why = recipe_ok(mt.group(1), grades)
        if not ok:
            err(f"考点组合不符合{mt.group(1)}的配方：{why}")
    if "**耦合链**" not in sec:
        err("缺少“耦合链”说明")
    mg = re.search(r"\*\*最高分级\*\*[：:]\s*(L\d)", sec)
    if not mg:
        err("缺少“最高分级”")
    elif grades and mg.group(1) != max(grades):
        err(f"最高分级应为 {max(grades)}，现在写的是 {mg.group(1)}")
    return tp, ids


def check_tp_file(main_path, require_cat=False):
    """检查和主文件同目录的 <标题>考点说明.md（内部校验用，不交给制作方）。"""
    folder = os.path.dirname(main_path)
    title = os.path.basename(main_path)[:-3]
    name = f"{title}考点说明.md"
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        if require_cat:
            err(f"缺少考点说明文件 {name}")
        else:
            warn(f"缺少考点说明文件 {name}（已有任务可以忽略；新任务必须有）")
        return None
    tp_path = find_up(folder, ".kiro/steering/animation-test-points.md") \
        or os.path.join(HERE, "..", "references", "test-points.md")
    if not os.path.exists(tp_path):
        warn("找不到考点表，跳过考点说明检查")
        return None
    e0, w0 = len(ERR), len(WARN)
    t = read(path)
    if not t.lstrip().startswith(f"# {title}考点说明"):
        err(f"标题应为“# {title}考点说明”")
    check_tp_section(t, tp_path)
    mt = re.search(r"\*\*题目档位\*\*[：:]\s*(基准档|进阶档|上限档)", t)
    ms = re.search(r"\*\*档位来源\*\*[：:]\s*(默认|用户指定)", t)
    if not ms:
        err("缺少“档位来源”（默认/用户指定）")
    if mt and mt.group(1) == "基准档":
        if not ms or ms.group(1) != "用户指定":
            err("档位低于进阶档：新任务默认至少进阶档；只有用户明确提到基准档时才能用基准档，"
                "并写“档位来源：用户指定”")
        else:
            warn("本题是基准档（用户指定），请确认用户确实明确提到了基准档")
    cat = None
    mc = re.search(r"\*\*主类目\*\*[：:]\s*(\S+)", t)
    if mc:
        cat = mc.group(1)
        tax = find_up(folder, ".kiro/steering/animation-taxonomy.md") \
            or os.path.join(HERE, "..", "references", "animation-taxonomy.md")
        if os.path.exists(tax):
            cats, _, _ = load_taxonomy(tax)
            if cat not in cats:
                err(f"主类目“{cat}”不在类目表中")
    elif require_cat:
        err("缺少“主类目”（一级/二级/三级）")
    if require_cat:
        tax = find_up(folder, ".kiro/steering/animation-taxonomy.md") \
            or os.path.join(HERE, "..", "references", "animation-taxonomy.md")
        check_tags(t, tax)
    ERR[e0:] = [f"{name}：{m}" for m in ERR[e0:]]
    WARN[w0:] = [f"{name}：{m}" for m in WARN[w0:]]
    return cat


def check_tags(text, tax_path):
    """检查“## 类目与标签”里的标签表是否符合类目表第三、四节的规则。"""
    sec = section(text, "## 类目与标签")
    if not sec:
        err("缺少“## 类目与标签”一节")
        return
    if not os.path.exists(tax_path):
        warn("找不到类目表，跳过标签检查")
        return
    _, tags, behaviors = load_taxonomy(tax_path)
    rows = table_rows(sec)
    if not rows or rows[0][:3] != ["标签组", "选定标签", "必要说明"]:
        err("标签表的表头应为：标签组｜选定标签｜必要说明")
        return
    seen, n_beh, n_main = set(), 0, 0
    for r in rows[1:]:
        if len(r) < 2:
            continue
        g, v = r[0], r[1]
        seen.add(g)
        if g not in ALL_GROUPS:
            err(f"未知的标签组“{g}”"); continue
        if v.startswith("不填") or v == "":
            if g in REQUIRED:
                err(f"必填标签组“{g}”没有填写")
            elif len(r) < 3 or not r[2].strip():
                warn(f"选填标签组“{g}”不填时，最好写一句理由")
            continue
        if g == "动画行为":
            n_beh += 1
            is_main = v.startswith("主行为")
            n_main += is_main
            path = re.sub(r"^(主行为|辅助行为)[：:]", "", v).strip()
            parts = tuple(x.strip() for x in path.split("/"))
            if len(parts) != 3 or parts not in behaviors:
                err(f"动画行为“{path}”不在类目表中（应写成 大类/行为类/标签名）")
            elif is_main and parts[0] not in MAIN_OK:
                err(f"主行为“{path}”的大类不能作为主行为")
            continue
        names = [re.sub(r"[（(].*?[）)]", "", x).strip() for x in re.split(r"[、,，]", v) if x.strip()]
        for n in names:
            if n not in tags.get(g, set()):
                err(f"标签组“{g}”里没有“{n}”")
        if g in SINGLE and len(names) != 1:
            err(f"标签组“{g}”只能单选，现在有 {len(names)} 个")
        if g == "材质质感" and not 1 <= len(names) <= 3:
            err("材质质感应为 1–3 个")
        if g == "应用场景" and len(names) > 2:
            err("应用场景最多 2 个")
    for g in sorted(ALL_GROUPS - seen):
        err(f"标签表缺少“{g}”这一组（选填组不填时写“不填”）")
    if not 1 <= n_beh <= 4:
        err(f"动画行为应为 1–4 个，现在有 {n_beh} 个")
    if n_main != 1:
        err(f"必须有且只有 1 个主行为，现在有 {n_main} 个")


GENERAL_BASELINE = {"PBR 贴图或程序化纹理": r"PBR|程序化纹理", "倒角": r"倒角", "接触阴影": r"接触阴影",
                    "AgX 色彩管理": r"AgX", "采样": r"采样", "100% 查看细节": r"100%", "尺度参照": r"尺度参照",
                    "防重复": r"重复"}
HEAVY_SIMS = {"液体模拟": r"液体模拟|FLIP", "烟雾模拟": r"烟雾模拟|烟火模拟", "布料模拟": r"布料模拟",
              "刚体模拟": r"刚体模拟"}
METHOD_WORDS = r"模拟|绑定|修改器|几何节点|驱动器|形态键|置换|散布|实例化|动态绘画|反向动力学|硬表面|程序化|体积|粒子|路径跟随|材质|遮罩|贴图|骨骼|自发光|建模|全局光照|光照门户|IES|力场|灯光"


def _clean_terms(s):
    s = re.sub(r"（[^）]*）|\([^)]*\)", "", s)
    return [x.strip(" 。") for x in re.split(r"[、，,]", s) if x.strip(" 。")]


def _plugin_key(name):
    n = re.sub(r"（[^）]*）|\([^)]*\)", "", name).strip()
    n = re.sub(r"^内置", "", n)
    m = re.match(r"[A-Za-z][\w.\-]*(?: [A-Z][\w.\-]*)*", n)
    return m.group(0) if m else n


def load_baseline(path):
    t = open(path, encoding="utf-8-sig").read()
    rows, mods = {}, {}
    for line in t.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(c) == 6 and c[0] not in ("二级类目",) and not c[0].startswith("-"):
            rows[c[0]] = {"terms": _clean_terms(c[3]), "plugins": [_plugin_key(p) for p in re.split(r"[、，,]", c[4]) if p.strip()],
                          "mods": re.findall(r"T\d+", c[5])}
    for m in re.finditer(r"## 技术模块 (T\d+)：.+?\n(.+?)(?=\n## 技术模块|\Z)", t, re.S):
        body = m.group(2)
        mt = re.search(r"\*\*专业术语\*\*：(.+)", body)
        plugs = [_plugin_key(r[0]) for r in table_rows(body)[1:] if r and r[0] != "插件"]
        mods[m.group(1)] = {"terms": _clean_terms(mt.group(1)) if mt else [], "plugins": plugs}
    return rows, mods


def check_baseline(t, tp_text, folder, cat):
    """3.3 起：按主类目检查主文件是否写进了制作底线、专业术语和推荐插件。"""
    base = find_up(folder, ".kiro/skills/animation-brief-advanced/references/production-baseline.md") \
        or os.path.join(HERE, "..", "references", "production-baseline.md")
    if not cat or not os.path.exists(base):
        warn("找不到主类目或 production-baseline.md，跳过制作底线检查")
        return
    rows, mods = load_baseline(base)
    parts = cat.split("/")
    second = parts[1] if len(parts) > 1 else ""
    if second not in rows:
        warn(f"production-baseline.md 里没有二级类目“{second}”，跳过类目底线检查")
        return
    row = rows[second]
    terms = list(dict.fromkeys(row["terms"] + [x for m in row["mods"] for x in mods.get(m, {}).get("terms", [])]))
    hit = [x for x in terms if x in t]
    need = max(5, -(-len(terms) * 3 // 10))
    if len(hit) < need:
        miss = [x for x in terms if x not in t]
        err(f"类目“{second}”和技术模块 {'、'.join(row['mods']) or '无'} 的专业术语只写进了 {len(hit)} 个，"
            f"至少要 {need} 个（还没用的有：{'、'.join(miss[:12])}）")
    plugs = list(dict.fromkeys(row["plugins"] + [x for m in row["mods"] for x in mods.get(m, {}).get("plugins", [])]))
    ms = re.search(r"可借助(.+?)(这些|等)插件", section(t, "## 底线和限制"), re.S)
    sentence = ms.group(1) if ms else ""
    ph = [p for p in plugs if p and p in sentence]
    if plugs and len(ph) < min(2, len(plugs)):
        err(f"插件建议里只写了 {len(ph)} 个类目推荐插件，至少要 2 个（可选：{'、'.join(plugs)}）")
    if parts[0] != "图形动画":
        for k, pat in GENERAL_BASELINE.items():
            if not re.search(pat, t):
                err(f"主文件缺少通用底线“{k}”")
    eff = section(t, "## 关键效果和做法", "## 灯光和画面")
    items = re.findall(r"^\d+\.\s*(.+)$", eff, re.M)
    for it in items:
        if not re.search(r"一镜到底|运镜|镜头", it.split("：", 1)[0]) and not re.search(METHOD_WORDS, it):
            warn(f"关键效果“{it[:12]}…”没有写用什么方法做（专业术语）")
    if items and not any(re.search(r"材质|质感", it.split("：", 1)[0]) for it in items):
        err("“关键效果和做法”里至少要有 1 条专门写材质和建模做法（标题里带“材质”或“质感”）")
    heavy = [k for k, pat in HEAVY_SIMS.items() if re.search(pat, t)]
    if len(heavy) > 2:
        err(f"重模拟有 {len(heavy)} 种（{'、'.join(heavy)}），最多 2 种，其余动态改用骨骼、驱动器、形态键等轻量做法")
    sec = section(tp_text, "## 制作底线清单", "## 类目与标签")
    if not sec:
        err("考点说明缺少“## 制作底线清单”一节（3.3 起必填）")
    else:
        m2 = re.search(r"\*\*二级类目\*\*[：:]\s*(\S+)", sec)
        if not m2 or m2.group(1) != second:
            err(f"制作底线清单的“二级类目”应为“{second}”")
        if "**技术模块**" not in sec:
            err("制作底线清单缺少“技术模块”")


COMPOSITION = r"三分法|引导线|框景|负空间|对角线|对称|中心构图|S 形|S形|剪影|层次纵深"
REAL_NUM = r"\d[\d.,]*\s*(秒|米|厘米|毫米|°|度|K|倍|%|赫兹|帧|克|千克|升|毫升|次|颗|条|只|根|段|层|处|个)|折射率\s*约?\s*\d"
CINE_DIMS = ["动态密度", "电影级画面", "细节精致度"]


def is_adv(tp_text):
    return bool(re.search(r"\*\*规范版本\*\*[：:]\s*进阶版", tp_text or ""))


def is_v34(tp_text):
    if is_adv(tp_text):
        return True
    m = re.search(r"\*\*规范版本\*\*[：:]\s*([\d.]+)", tp_text or "")
    return bool(m) and tuple(int(x) for x in m.group(1).split(".")[:2]) >= (3, 4)


AGX_LOOKS = ["Very High Contrast", "Medium High Contrast", "Medium Low Contrast", "Very Low Contrast",
             "High Contrast", "Low Contrast", "Base Contrast", "Punchy", "Greyscale"]
ADV_DIMS = ["海报帧与视觉基调"]
COORD = r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)"


def _range(cell):
    m = re.search(r"([\d.]+)\s*[–-]\s*([\d.]+)", cell)
    return (float(m.group(1)), float(m.group(2))) if m else None


def load_tones(folder):
    p = find_up(folder, ".kiro/skills/animation-brief-advanced/references/visual-tones.md") \
        or os.path.join(HERE, "..", "references", "visual-tones.md")
    if not os.path.exists(p):
        return None
    rows = table_rows(open(p, encoding="utf-8-sig").read())
    if not rows:
        return None
    head = rows[0]
    col = {h: i for i, h in enumerate(head)}
    out = {}
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        g = lambda k: next((r[i] for h, i in col.items() if h.startswith(k)), "")
        out[r[0]] = {
            "ratio": _range(g("主辅光比")), "focal": _range(g("焦距")),
            "turn": float(re.search(r"[\d.]+", g("镜头转动上限")).group(0)),
            "move": float(re.search(r"[\d.]+", g("镜头移动上限")).group(0)) / 100,
            "looks": [x.strip() for x in re.split(r"[、,，]", g("AgX 观感")) if x.strip()],
        }
    return out


def _sub(a, b): return [a[i] - b[i] for i in range(3)]
def _dot(a, b): return sum(a[i] * b[i] for i in range(3))
def _cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def _norm(a):
    n = _dot(a, a) ** 0.5
    return [x / n for x in a] if n else a


def project(cam, aim, subj, focal, sensor=36.0, aspect=16 / 9):
    """按 Blender 默认（传感器宽 36 毫米、按宽适配、不侧倾）把主体投影到画面，返回 (横, 纵, 深度)。"""
    f = _norm(_sub(aim, cam))
    r = _norm(_cross(f, [0, 0, 1]))
    u = _cross(r, f)
    d = _sub(subj, cam)
    zc = _dot(d, f)
    if zc <= 0:
        return None
    x = 0.5 + focal * _dot(d, r) / zc / sensor
    y = 0.5 - focal * _dot(d, u) / zc / (sensor / aspect)
    return x, y, zc


def check_advanced(t, tp_text, T, fps, segs, folder):
    scene = section(t, "## 场景和主体", "## 动作和镜头")
    act = section(t, "## 动作和镜头", "## 关键效果和做法")
    eff = section(t, "## 关键效果和做法", "## 灯光和画面")
    light = section(t, "## 灯光和画面", "## 底线和限制")

    # 一、视觉基调
    tones = load_tones(folder)
    tone = None
    m = re.search(r"视觉基调[：:]\s*([^。，,\s（(]+)", light.strip().split("\n", 1)[0])
    mt = re.search(r"\*\*视觉基调\*\*[：:]\s*(\S+)", tp_text)
    if not m:
        err("“灯光和画面”第一句应写“视觉基调：<基调名>。”")
    elif tones is None:
        warn("找不到 visual-tones.md，跳过视觉基调检查")
    elif m.group(1) not in tones:
        err(f"视觉基调“{m.group(1)}”不在 visual-tones.md 里（可选：{'、'.join(tones)}）")
    else:
        tone = tones[m.group(1)]
        if not mt or mt.group(1) != m.group(1):
            err(f"考点说明的“视觉基调”应为“{m.group(1)}”")
    if tone:
        for a in re.findall(r"光比约?\s*(\d+(?:\.\d+)?)\s*[:：]\s*1", light):
            lo, hi = tone["ratio"]
            if not lo - 1e-9 <= float(a) <= hi + 1e-9:
                err(f"光比 {a}:1 不在视觉基调的范围 {fmt_num(lo)}–{fmt_num(hi)}:1 内")
        looks = re.findall("|".join(AGX_LOOKS), light)
        if not looks:
            err("没有写 AgX 观感的名称（例如 Punchy、Base Contrast）")
        for lk in set(looks):
            if lk not in tone["looks"]:
                err(f"AgX 观感 {lk} 不在视觉基调允许的范围内（可选：{'、'.join(tone['looks'])}）")

    # 二、关键机位（逐行带标签，不用表格）
    if "坐标：" not in scene and "坐标:" not in scene:
        err("“场景和主体”里没有写坐标系（“坐标：原点在……，x 朝……”）")
    cam_part = act.split("关键机位", 1)[1] if "关键机位" in act else ""
    if not cam_part:
        err("“动作和镜头”末尾缺少关键机位（“关键机位（传感器宽 36 毫米……）：”加逐行的机位）")
    else:
        if "36 毫米" not in cam_part.split("\n", 1)[0]:
            err("关键机位前的说明里要写“传感器宽 36 毫米”")
        if re.search(r"^\|.*机位.*\|", cam_part, re.M):
            err("关键机位要写成逐行带标签的文字，不用表格（复制粘贴时表格容易丢失列边界）")
        # 每一条不依赖换行，换行被合并成一行也能逐条认出来
        heads = list(re.finditer(r"第\s*([\d.]+)\s*秒[：:]\s*机位", cam_part))
        pts = []
        for i, h in enumerate(heads):
            body = cam_part[h.start(): heads[i + 1].start() if i + 1 < len(heads) else len(cam_part)]
            tm = h.group(1)
            m = re.search(r"机位\s*" + COORD + r"\s*[，,]\s*看向\s*" + COORD + r"\s*[，,]\s*主体\s*" + COORD +
                          r"\s*[，,]\s*焦距\s*([\d.]+)\s*毫米\s*[，,]\s*对焦距离\s*([\d.]+)\s*米\s*[，,]\s*"
                          r"主体在画面横向\s*([\d.]+)\s*[、，,]\s*纵向\s*([\d.]+)\s*[；;]\s*运镜[：:]\s*(\S[^\n]*)", body)
            if not m:
                err(f"关键机位第 {tm} 秒这一条的格式不对，应为“第 T 秒：机位 (x, y, z)，看向 (x, y, z)，主体 (x, y, z)，"
                    f"焦距 N 毫米，对焦距离 N 米，主体在画面横向 a、纵向 b；运镜：……”"); continue
            g = [float(x) for x in m.groups()[:13]]
            pts.append((float(tm), g[0:3], g[3:6], g[6:9], g[9], g[10], g[11], g[12]))
        if not heads:
            err("关键机位里没有认出任何一条（“第 T 秒：机位 (x, y, z)，……”）")
        times = [p[0] for p in pts]
        if times != sorted(times) or len(set(times)) != len(times):
            err("关键机位的时刻应从小到大、不重复")
        need = sorted({float(s) for s, _, _ in segs} | ({T} if T else set()))
        miss = [fmt_num(x) for x in need if not any(abs(x - y) < 1e-6 for y in times)]
        if miss:
            err(f"关键机位缺少这些时刻：第 {'、'.join(miss)} 秒（每段的起点和结尾都要有）")
        for tm, cam, aim, subj, focal, fd, sx, sy in pts:
            pr = project(cam, aim, subj, focal)
            if not pr:
                err(f"第 {fmt_num(tm)} 秒：主体在镜头后面"); continue
            px, py, _ = pr
            dist = _dot(_sub(subj, cam), _sub(subj, cam)) ** 0.5
            if abs(px - sx) > 0.07 or abs(py - sy) > 0.07:
                err(f"第 {fmt_num(tm)} 秒：按坐标和 {fmt_num(focal)} 毫米焦距算，主体在画面 ({px:.2f}, {py:.2f})，"
                    f"机位里写的是 ({sx:.2f}, {sy:.2f})")
            if not (0.05 <= px <= 0.95 and 0.05 <= py <= 0.95):
                err(f"第 {fmt_num(tm)} 秒：主体在画面边缘或画外 ({px:.2f}, {py:.2f})")
            if dist and abs(fd - dist) / dist > 0.2:
                err(f"第 {fmt_num(tm)} 秒：对焦距离 {fmt_num(fd)} 米和镜头到主体的距离约 {dist:.0f} 米差得太多")
            if tone:
                lo, hi = tone["focal"]
                if not lo <= focal <= hi:
                    err(f"第 {fmt_num(tm)} 秒：焦距 {fmt_num(focal)} 毫米不在视觉基调的范围 {fmt_num(lo)}–{fmt_num(hi)} 毫米内")
        import math
        for a, b in zip(pts, pts[1:]):
            dt = b[0] - a[0]
            if dt <= 0:
                continue
            fa, fb = _norm(_sub(a[2], a[1])), _norm(_sub(b[2], b[1]))
            ang = math.degrees(math.acos(max(-1.0, min(1.0, _dot(fa, fb))))) / dt
            mv = _dot(_sub(b[1], a[1]), _sub(b[1], a[1])) ** 0.5 / dt
            da = _dot(_sub(a[3], a[1]), _sub(a[3], a[1])) ** 0.5
            db = _dot(_sub(b[3], b[1]), _sub(b[3], b[1])) ** 0.5
            rel = mv / max(1e-6, min(da, db))
            if tone and ang > tone["turn"] + 1e-6:
                err(f"第 {fmt_num(a[0])}–{fmt_num(b[0])} 秒：镜头每秒转 {ang:.1f}°，超过视觉基调的上限 {fmt_num(tone['turn'])}°/秒")
            if tone and rel > tone["move"] + 1e-6:
                err(f"第 {fmt_num(a[0])}–{fmt_num(b[0])} 秒：镜头每秒移动 {mv:.1f} 米，占主体距离 {rel:.0%}，"
                    f"超过视觉基调的上限 {tone['move']:.0%}")
        # 写了三分法的段落，主体要在三分线附近
        for s, e, name in segs:
            blk = re.search(r"^第\s*" + re.escape(s) + r"\s*–\s*" + re.escape(e) + r"\s*秒（[^）]+）(.+)$", act, re.M)
            if not blk or "三分法" not in blk.group(1):
                continue
            row = next((p for p in pts if abs(p[0] - float(s)) < 1e-6), None)
            if row and not any(min(abs(v - 1 / 3), abs(v - 2 / 3)) <= 0.08 for v in (row[6], row[7])):
                err(f"段落“{name}”写了三分法，但第 {s} 秒主体在画面 ({row[6]:.2f}, {row[7]:.2f})，不在三分线附近")

    # 三、海报帧
    m = re.search(r"海报帧共\s*(\d+)\s*帧", light)
    lines = re.findall(r"^-\s*第\s*(\d+)\s*帧（第\s*([\d.]+)\s*秒）[：:](.+)$", light, re.M)
    if not m:
        err("“灯光和画面”缺少海报帧（“海报帧共 N 帧……”）")
    else:
        n = int(m.group(1))
        if not 2 <= n <= 3:
            err(f"海报帧应为 2–3 帧，现在写的是 {n} 帧")
        if len(lines) != n:
            err(f"海报帧写的是 {n} 帧，实际列出 {len(lines)} 帧")
        if "自查" not in light:
            err("海报帧要写明先用低分辨率渲染出来自查")
        for f, sec, body in lines:
            if fps and int(f) != round(float(sec) * fps):
                err(f"海报帧第 {f} 帧和第 {sec} 秒对不上（应为第 {round(float(sec) * fps)} 帧）")
            if T and not 0 <= float(sec) <= T:
                err(f"海报帧第 {sec} 秒超出片长")
            for k in ("构图", "最亮", "焦点", "色"):
                if k not in body:
                    err(f"海报帧第 {f} 帧没有写“{k}”")

    # 四、渲染设置
    m = re.search(r"渲染设置[：:]([^\n]+)", light)
    if not m:
        err("“灯光和画面”缺少“渲染设置：……”")
    else:
        r = m.group(1)
        for pat, label in ((r"Cycles|EEVEE", "渲染引擎"), (r"采样\s*\d+", "采样数"),
                           (r"透射反弹\s*\d+\s*次", "透射反弹次数"), (r"焦散", "焦散开或关"),
                           (r"曝光值?\s*[-+]?\d", "曝光值"), (r"快门", "运动模糊快门")):
            if not re.search(pat, r):
                err(f"渲染设置里没有写{label}")
        if re.search(r"体积", t) and not (re.search(r"体积反弹\s*\d+\s*次", r) and "体积步长" in r):
            err("片子里有体积，渲染设置要写体积反弹次数和体积步长")

    # 五、色值和光强
    if len(re.findall(r"#[0-9A-Fa-f]{6}\b", light)) < 3:
        err("配色方案里至少要给主色、辅色和点缀色各一个十六进制色值")
    if len(re.findall(r"强度约?\s*[\d.]+", light)) < 3:
        err("“灯光和画面”至少要给 3 层光写出强度（“强度约 N 瓦”等）")

    # 六、明暗分区
    if not re.search(r"明暗分区[：:]", light) or "档" not in section(light, "明暗分区"):
        err("“灯光和画面”缺少“明暗分区：……”，或没有写主体和背景差几档")

    # 七、优先级和退一步
    items = re.findall(r"^\d+\.\s*(.+)$", eff, re.M)
    pri = []
    for it in items:
        head = it.split("：", 1)[0]
        mm = re.search(r"必须|尽量|可省", head)
        if not mm:
            err(f"关键效果“{head[:12]}…”的标题没有注明优先级（必须、尽量或可省）")
        else:
            pri.append(mm.group(0))
        if not re.search(r"一镜到底|运镜|镜头", head) and "退一步" not in it:
            err(f"关键效果“{head[:12]}…”没有写“退一步可以……”的替代做法")
    if items and "必须" not in pri:
        err("关键效果里至少要有 1 条“必须”")


def check_cinematic(t, T, segs):
    """3.4 起：动态总表、还原数值、电影级光线/构图/色彩和细节精致度都要写进主文件。"""
    scene = section(t, "## 场景和主体", "## 动作和镜头")
    act = section(t, "## 动作和镜头", "## 关键效果和做法")
    eff = section(t, "## 关键效果和做法", "## 灯光和画面")
    light = section(t, "## 灯光和画面", "## 底线和限制")

    # 一、动态总表
    m = re.search(r"全片在动的东西共\s*(\d+)\s*类[：:](.+)", act)
    if not m:
        err("“动作和镜头”末尾缺少动态总表（“全片在动的东西共 N 类：……”）")
    else:
        n = int(m.group(1))
        items = [x for x in re.split(r"[；;]", m.group(2).strip().rstrip("。")) if x.strip()]
        if n < 8:
            err(f"动态总表只有 {n} 类，至少要 8 类")
        if len(items) != n:
            err(f"动态总表写的是 {n} 类，实际列出 {len(items)} 类")
        spans = []
        for it in items:
            mm = re.search(r"（第\s*([\d.]+)\s*[–-]\s*([\d.]+)\s*秒）", it)
            if mm:
                spans.append((float(mm.group(1)), float(mm.group(2))))
            elif "（全片）" in it:
                spans.append((0.0, T or 0.0))
            else:
                err(f"动态总表里“{it.strip()[:10]}…”没有标出时段（“（第 X–Y 秒）”或“（全片）”）")
        if "远景" not in m.group(2):
            err("动态总表里没有远景的动态（至少 1 类写明在远景）")
        if T and spans:
            w = 0.0
            while w + 2 <= T + 1e-9:
                c = sum(1 for s, e in spans if min(e, w + 2) - max(s, w) > 1e-6)
                if c < 3:
                    err(f"从第 {fmt_num(w)} 秒到第 {fmt_num(w + 2)} 秒只有 {c} 类动态，任意 2 秒至少要 3 类")
                    break
                w += 0.5
        for s, e, name in segs:
            s, e = float(s), float(e)
            if not any(s - 1e-6 <= a < e for a, _ in spans):
                err(f"段落“{name}”里没有新动态出场（动态总表里没有从这段开始的动态）")

    # 四、每段构图、特写、焦点
    blocks = re.split(r"^(?=第\s*[\d.]+\s*–\s*[\d.]+\s*秒（)", act, flags=re.M)
    for b in blocks:
        hm = re.match(r"第\s*[\d.]+\s*–\s*[\d.]+\s*秒（([^）]+)）", b)
        if not hm:
            continue
        body = b.split("全片在动的东西共")[0]
        if "构图" not in body or not re.search(COMPOSITION, body):
            err(f"段落“{hm.group(1)}”没有写构图（要有“构图”二字和三分法、引导线、框景、负空间、对角线等方式）")
    if "特写" not in act:
        err("“动作和镜头”里没有安排近景特写")
    if not re.search(r"\d+\s*毫米", act + light):
        err("没有写镜头焦距（毫米）")
    if not re.search(r"f/\s*\d", t):
        err("没有写光圈（f/ 数值）")
    if "焦点" not in act + light:
        err("没有写焦点怎么安排（焦点转移，或说明不做焦点转移）")

    # 二、还原数值
    for it in re.findall(r"^\d+\.\s*(.+)$", eff, re.M):
        head = it.split("：", 1)[0]
        if re.search(r"一镜到底|运镜|镜头", head):
            continue
        if not re.search(REAL_NUM, it.split("：", 1)[-1]):
            err(f"关键效果“{head[:12]}…”没有写真实世界的数值作还原依据")

    # 三、五、光线、氛围和色彩
    if not re.search(r"[三四五六3-6]\s*层", light):
        err("“灯光和画面”至少要写 3 层光")
    if not re.search(r"轮廓光|逆光|实用光", light):
        err("“灯光和画面”没有轮廓光、逆光或实用光")
    nk = len(re.findall(r"\d[\d,]{2,5}\s*K", light))
    if nk < 3:
        err(f"“灯光和画面”只写了 {nk} 个色温（K），至少要 3 个")
    if "光比" not in light or not re.search(r"\d+(\.\d+)?\s*[:：]\s*1", light):
        err("“灯光和画面”没有写主辅光比（例如“光比约 4:1”）")
    if not re.search(r"体积光|空气透视|体积雾|微尘|水汽|体积散射", light):
        err("“灯光和画面”没有大气效果（体积光、空气透视、局部体积雾、微尘或水汽）")
    for k in ("主色", "辅色", "点缀色", "色彩脚本", "暗角", "颗粒"):
        if k not in light:
            err(f"“灯光和画面”缺少“{k}”")

    # 六、细节精致
    for k in ("大形", "中形", "小形"):
        if k not in scene:
            err(f"“场景和主体”没有按三级写细节（缺“{k}”）")
    m = re.search(r"微细节共\s*(\d+)\s*处[：:]([^\n]+)", scene)
    if not m:
        err("“场景和主体”缺少微细节清单（“微细节共 N 处：……”）")
    else:
        n = int(m.group(1))
        k = len([x for x in re.split(r"[；;]", m.group(2).rstrip("。")) if x.strip()])
        if n < 6:
            err(f"微细节只有 {n} 处，至少要 6 处")
        if k != n:
            err(f"微细节写的是 {n} 处，实际列出 {k} 处")


HARD_COMMON = ["结构分件", "递进阶段", "布光层次"]
HARD_BY_TOP = {
    "产品动画": ["产品行为", "卖点细节", "组件数量", "材质种类"],
    "场景动画": ["资产种类", "环境动态源", "三层空间"],
    "载具动画": ["状态转换"],
    "图形动画": ["组织状态", "元素关系"],
    "现象动画": ["触发与交互"],
    "科教演示": ["观察方法"],
    "角色动画": [],
}


V3_HEADS = ["## 场景和主体", "## 动作和镜头", "## 关键效果和做法", "## 灯光和画面", "## 底线和限制"]
NEGATION = r"(不使用|不能使用|不能用|不用|不能出现|禁止使用|禁止|不导入|不能导入|别用|别)[^；。]*"
COMMERCIAL = (r"Hard ?Ops|Boxcutter|Launch Control|Auto-Rig Pro|The Grove|Geo-Scatter|RBDLab|Simply Cloth|"
              r"Physical Starlight|SceneCity|Photographer|Gaffer|FLIP Fluids|Botaniq|DECALmachine|KitOps")


def fmt_num(x):
    return f"{x:g}"


def check_rubric(folder, rng, cat=None, v34=False, adv=False):
    """检查任务文件夹里的 rubric.json。rng 是主文件里的允许时长区间 (A, B)。"""
    import json
    path = os.path.join(folder, "rubric.json")
    if not os.path.exists(path):
        err("缺少 rubric.json")
        return
    e0, w0 = len(ERR), len(WARN)
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        err("应为不带 BOM 的 UTF-8")
        raw = raw[3:]
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        err(f"不是合法的 JSON：{e}")
        data = None
    if isinstance(data, dict):
        sp = data.get("scoring_policy", {})
        want = {"aggregation": "weighted_sum", "total_weight": 100, "total_threshold": 85,
                "require_all_critical_pass": True}
        for k, v in want.items():
            if sp.get(k) != v:
                err(f"scoring_policy.{k} 应为 {json.dumps(v)}")
        if not str(data.get("task", "")).strip():
            err("缺少 task")
        crit = data.get("criteria")
        if not isinstance(crit, list) or not crit:
            err("criteria 为空")
            crit = []
        hi = 26 if adv else (25 if v34 else 22)
        if crit and not 12 <= len(crit) <= hi:
            warn(f"评价项有 {len(crit)} 项，一般为 {'20–26' if adv else ('19–25' if v34 else '15–22')} 项")
        total, n_crit, dur_ok = 0, 0, False
        for i, c in enumerate(crit, 1):
            tag = f"第 {i} 项"
            if not isinstance(c, dict):
                err(f"{tag} 不是对象"); continue
            cid = c.get("criterion_id")
            if cid != f"R{i:02d}":
                err(f"{tag} 的编号应为 R{i:02d}，现在是 {cid}")
            tag = cid or tag
            for k in ("dimension", "criterion"):
                if not str(c.get(k, "")).strip():
                    err(f"{tag} 缺少 {k}")
            w = c.get("weight")
            if not isinstance(w, (int, float)) or isinstance(w, bool) or w <= 0:
                err(f"{tag} 的 weight 应为正数")
            else:
                total += w
            cr = c.get("critical")
            if cr is True:
                n_crit += 1
                if c.get("pass_threshold") != 100:
                    err(f"{tag} 是关键项，pass_threshold 应为 100")
            elif cr is False:
                if c.get("pass_threshold") is not None:
                    err(f"{tag} 不是关键项，pass_threshold 应为 null")
            else:
                err(f"{tag} 的 critical 应为 true 或 false")
            st = c.get("scoring_type")
            keys = {"binary": {"0", "100"}, "discrete": {"0", "50", "100"}}.get(st)
            if keys is None:
                err(f"{tag} 的 scoring_type 只能是 binary 或 discrete")
            else:
                an = c.get("score_anchors", {})
                if not isinstance(an, dict) or set(an) != keys:
                    err(f"{tag} 的 score_anchors 应正好包含 {sorted(keys, key=int)}")
                elif any(not str(v).strip() or "……" in str(v) or "..." in str(v) for v in an.values()):
                    err(f"{tag} 的锚点有空白或省略号")
            if str(c.get("dimension", "")).strip() == "时长":
                text = str(c.get("criterion", "")) + "".join(str(v) for v in c.get("score_anchors", {}).values())
                if rng and fmt_num(rng[0]) in text and fmt_num(rng[1]) in text:
                    dur_ok = True
                if st != "binary":
                    warn(f"{tag}（时长）一般用 binary")
        need = list(HARD_COMMON)
        if cat:
            top = cat.split("/")[0]
            if top in HARD_BY_TOP:
                need += HARD_BY_TOP[top]
            else:
                warn(f"不认识主类目的一级类目“{top}”，只检查通用硬指标")
        else:
            warn("没有主类目，只检查通用硬指标")
        by_dim = {str(c.get("dimension", "")).strip(): c for c in crit if isinstance(c, dict)}
        for d in need:
            c = by_dim.get(d)
            if not c:
                err(f"缺少数量硬指标项“{d}”（dimension 要和 SKILL.md 3.7 的维度名一致）")
                continue
            if c.get("critical") is not True:
                err(f"数量硬指标项“{d}”应为关键项")
            if not re.search(r"\d", str(c.get("criterion", ""))):
                err(f"数量硬指标项“{d}”的 criterion 里没有写出数量")
        mq = by_dim.get("材质与制作底线")
        if not mq:
            err("缺少关键项“材质与制作底线”（3.3 起必填）")
        elif mq.get("critical") is not True:
            err("“材质与制作底线”应为关键项")
        if adv:
            for d in ADV_DIMS:
                c = by_dim.get(d)
                if not c:
                    err(f"缺少关键项“{d}”（进阶版必填）")
                elif c.get("critical") is not True:
                    err(f"“{d}”应为关键项")
        if v34:
            for d in CINE_DIMS:
                c = by_dim.get(d)
                if not c:
                    err(f"缺少关键项“{d}”（3.4 起必填）")
                elif c.get("critical") is not True:
                    err(f"“{d}”应为关键项")
        if abs(total - 100) > 1e-9:
            err(f"权重合计应为 100，现在是 {fmt_num(total)}")
        if not n_crit:
            err("没有关键项")
        if rng and not dur_ok:
            err(f"时长项没有写出主文件的允许区间 {fmt_num(rng[0])}–{fmt_num(rng[1])} 秒")
        if re.search(r"考点|L[1-4]\b|进阶档|上限档|基准档", raw.decode("utf-8", "ignore")):
            err("rubric 里不应写考点、分级或档位")
    elif data is not None:
        err("顶层应为对象")
    ERR[e0:] = [f"rubric.json：{m}" for m in ERR[e0:]]
    WARN[w0:] = [f"rubric.json：{m}" for m in WARN[w0:]]


def check_v3(path):
    t = read(path)
    title = os.path.basename(path)[:-3]
    if re.search(r"(v\d|版本|新版|修订|样稿|_\d+$)", title, re.I):
        err("标题里带有版本号")
    if not t.lstrip().startswith(f"# {title}\n"):
        err(f"第一行应为“# {title}”")
    pos = [t.find(h) for h in V3_HEADS]
    for h, p in zip(V3_HEADS, pos):
        if p < 0:
            err(f"缺少“{h}”一节")
    if all(p >= 0 for p in pos) and pos != sorted(pos):
        err("五个二级标题的顺序应为：" + " → ".join(h[3:] for h in V3_HEADS))
    first = t.split("\n## ", 1)[0].split("\n", 1)[-1].strip()
    if not first.startswith("用 Blender 5.0.0 做一条"):
        err("开头应写成“用 Blender 5.0.0 做一条……”")
    mt = re.search(r"做一条\s*约?\s*([\d.]+)\s*秒", first)
    mr = re.search(r"时长允许\s*([\d.]+)\s*[–-]\s*([\d.]+)\s*秒", first)
    T = float(mt.group(1)) if mt else None
    rng = (float(mr.group(1)), float(mr.group(2))) if mr else None
    if T is None:
        err("开头没有写目标时长（“做一条 T 秒的……”）")
    if not rng:
        err("开头没有写允许区间（“时长允许 A–B 秒”）")
    else:
        a, b = rng
        if a < 8 or b > 15.6 or a > b:
            err(f"允许区间 {fmt_num(a)}–{fmt_num(b)} 秒应在 8–15.6 秒以内")
        elif b > 12:
            warn(f"允许区间上限 {fmt_num(b)} 秒超过 12 秒，需确认用户已同意")
        if T is not None and not a <= T <= b:
            err(f"目标时长 {fmt_num(T)} 秒不在允许区间内")
    res = set(re.findall(r"(\d{3,4})×(\d{3,4})", t))
    fps = set(re.findall(r"(\d+)\s*帧/秒", t))
    if len(res) != 1 or len(fps) != 1:
        err(f"分辨率或帧率不一致或缺失：{res or '无'} / {fps or '无'}")
    mf = re.search(r"共\s*(\d+)\s*帧", first)
    if not mf:
        err("开头没有写总帧数")
    elif T and len(fps) == 1 and int(mf.group(1)) != round(T * int(next(iter(fps)))):
        err(f"总帧数 {mf.group(1)} 和目标时长×帧率不一致")
    if "没有声音" not in first and "无声音" not in first:
        err("开头没有写“没有声音”")
    out_spec = find_up(os.path.dirname(path), ".kiro/steering/animation-output-spec.md")
    if out_spec and len(res) == 1 and len(fps) == 1:
        o = open(out_spec, encoding="utf-8-sig").read()
        orr = re.search(r"(\d{3,4})×(\d{3,4})", o); ofr = re.search(r"(\d+)\s*帧/秒", o)
        if orr and ofr and ((orr.group(1), orr.group(2)) not in res or ofr.group(1) not in fps):
            warn("分辨率/帧率与 animation-output-spec.md 的默认值不同，需确认是用户要求的")
    act = section(t, "## 动作和镜头", "## 关键效果和做法")
    segs = re.findall(r"^第\s*([\d.]+)\s*–\s*([\d.]+)\s*秒（([^）]+)）", act, re.M)
    if len(segs) < 4:
        err(f"“动作和镜头”应至少有 4 个“第 X–Y 秒（段落名）”段落，现在有 {len(segs)} 个")
    if segs:
        prev = 0.0
        for s, e, name in segs:
            s, e = float(s), float(e)
            if abs(s - prev) > 1e-6:
                err(f"段落“{name}”从第 {fmt_num(s)} 秒开始，应接在第 {fmt_num(prev)} 秒")
            if e <= s:
                err(f"段落“{name}”的时间范围不对")
            prev = e
        if T and abs(prev - T) > 1e-6:
            err(f"最后一段结束于 {fmt_num(prev)} 秒，和目标时长 {fmt_num(T)} 秒不一致")
        if T and len(segs) >= 1:
            last_len = float(segs[-1][1]) - float(segs[-1][0])
            if last_len < 1:
                warn("最后一段不到 1 秒，结果可能看不清")
        lens = [float(e) - float(s) for s, e, _ in segs]
        if max(lens) > 3.5:
            warn(f"有段落长达 {fmt_num(max(lens))} 秒，确认每 2–3 秒都有新变化")
    if not re.search(r"画面(停|在)[^。]*(结束|那一刻)", act):
        warn("最后一段没有写画面在什么时刻结束")
    eff = section(t, "## 关键效果和做法", "## 灯光和画面")
    items = re.findall(r"^\d+\.\s*(.+)$", eff, re.M)
    if len(items) < 4:
        warn(f"“关键效果和做法”只有 {len(items)} 条，一般不少于 4 条")
    for it in items:
        if not re.search(r"（(第\s*[\d.]+\s*[–-]\s*[\d.]+\s*秒|全片)", it[:40]):
            warn(f"关键效果“{it[:12]}…”没有在标题后标出时段")
    scene = section(t, "## 场景和主体", "## 动作和镜头")
    if len(scene) < 800:
        warn("“场景和主体”内容偏少，确认三层空间、8 类元素和尺度参照都已写出")
    for pat, label in ((r"bpy|\bAPI\b|Python|python|(?<!色彩)脚本|代码|函数", "代码或编程相关的词"),
                       (r"\b[a-z]+_[a-z_]+\b", "像属性变量名的英文"),
                       (r"\b[a-z]+\.[a-z_]+\(", "像函数调用的写法"),
                       (r"`", "代码格式的反引号")):
        mm = re.search(pat, t)
        if mm:
            err(f"正文里出现了{label}：“{mm.group(0)}”")
    for pat, label in ((r"考点|考题|考察", "“考点/考题/考察”字样"), (r"\bL[1-4]\b", "L1–L4 分级"),
                       (r"题目档位|基准档|进阶档|上限档", "题目档位"), (r"耦合链", "耦合链"),
                       (r"\*\*类目\*\*", "类目")):
        mm = re.search(pat, t)
        if mm:
            err(f"文件里出现了{label}：“{mm.group(0)}”（考点、分级、档位和类目不写进主文件）")
    positive = re.sub(NEGATION, "", t)
    mm = re.search(r"BlenderKit|Sketchfab|KitBash|素材库|HDRI|环境贴图|扫描模型|现成的?模型|模型资产", positive)
    if mm:
        err(f"正文里出现了外部素材：“{mm.group(0)}”（只允许插件和贴图）")
    mm = re.search(COMMERCIAL, t)
    if mm:
        err(f"正文里出现了商业插件：“{mm.group(0)}”")
    if "可借助" not in section(t, "## 底线和限制"):
        warn("“底线和限制”里没有插件建议（“可借助……等插件”）")
    if not re.search(r"立方体|基本几何体", t):
        warn("没有写“别用基本几何体拼凑主体”这条底线")
    folder = os.path.dirname(path)
    light = section(t, "## 灯光和画面", "## 底线和限制")
    if not re.search(r"[两三四五2-5]\s*层", light):
        warn("“灯光和画面”没有写明分几层光（布光层次 ≥ 2 层）")
    cat = check_tp_file(path, require_cat=True)
    tpp = os.path.join(folder, f"{title}考点说明.md")
    tp_text = open(tpp, encoding="utf-8-sig").read() if os.path.exists(tpp) else ""
    v34 = is_v34(tp_text)
    has_script = os.path.exists(os.path.join(folder, f"{title}剧本.md"))
    if has_script:
        (err if v34 else warn)("3.x 格式不再输出单独的剧本文件，所有内容都写进主文件")
    e0 = len(ERR)
    check_baseline(t, tp_text, folder, cat)
    ERR[e0:] = [f"制作底线：{m}" for m in ERR[e0:]]
    adv = is_adv(tp_text)
    if v34:
        e0 = len(ERR)
        check_cinematic(t, T, segs)
        ERR[e0:] = [f"电影级画面：{m}" for m in ERR[e0:]]
    if adv:
        e0 = len(ERR)
        fps_v = int(next(iter(fps))) if len(fps) == 1 else None
        check_advanced(t, tp_text, T, fps_v, segs, folder)
        ERR[e0:] = [f"可执行参数：{m}" for m in ERR[e0:]]
    else:
        warn("考点说明没有“**规范版本**：进阶版 1.0”，没有按进阶版规则检查")
    check_rubric(folder, rng, cat, v34, adv)
    report()


def check_single(path, tax_path):
    t = read(path)
    if TOPIC_H not in t:
        err(f"缺少“{TOPIC_H}”一节")
        report(); return
    topic = section(t, TOPIC_H)
    paras = [x.strip() for x in topic.split("\n\n") if x.strip()]
    first = paras[0] if paras else ""
    m = re.match(r"基于《(.+?剧本)》，用 Blender 5\.0\.0", first)
    if not m:
        err("开头应写成“基于《X剧本》，用 Blender 5.0.0 制作……”")
    else:
        if f"以下是《{m.group(1)}》：" not in topic:
            err(f"缺少“以下是《{m.group(1)}》：”这一句，剧本正文要接在它后面")
        else:
            sp = os.path.join(os.path.dirname(path), f"{m.group(1)}.md")
            if not os.path.exists(sp):
                err(f"缺少只有剧本的文件 {m.group(1)}.md")
            else:
                st = read(sp)
                body = t.split(f"以下是《{m.group(1)}》：", 1)[1].strip()
                expect = f"# {m.group(1)}\n\n{body}"
                if st.strip() != expect.strip():
                    err(f"{m.group(1)}.md 的内容和主文件里的剧本正文不一致，需要重新同步")
    for pat, label in ((r"bpy|\bAPI\b|Python|python|(?<!色彩)脚本|代码|函数", "代码或编程相关的词"),
                       (r"\b[a-z]+_[a-z_]+\b", "像属性变量名的英文"),
                       (r"\b[a-z]+\.[a-z_]+\(", "像函数调用的写法"),
                       (r"`", "代码格式的反引号")):
        mm = re.search(pat, topic)
        if mm:
            err(f"正文里出现了{label}：“{mm.group(0)}”")
    positive = re.sub(r"(不使用|不能使用|不能用|不用|不能出现|禁止使用|禁止|不导入|不能导入)[^；。]*", "", topic)
    mm = re.search(r"BlenderKit|Sketchfab|KitBash|素材库|HDRI|环境贴图|扫描模型|现成的?模型|模型资产", positive)
    if mm:
        err(f"正文里出现了外部素材：“{mm.group(0)}”（项目只允许插件和贴图，不允许其他素材）")
    mm = re.search(r"Hard ?Ops|Boxcutter|Launch Control|Auto-Rig Pro|The Grove|Geo-Scatter|RBDLab|Simply Cloth|Physical Starlight|SceneCity|Photographer|Gaffer|FLIP Fluids|Botaniq|DECALmachine|KitOps", topic)
    if mm:
        err(f"正文里出现了商业插件：“{mm.group(0)}”（只用内置和开源插件）")
    if "可借助" not in topic.split("以下是《")[0]:
        warn("Prompt 里没有插件建议（“可借助……等插件”）")
    if "基本几何体" not in topic:
        warn("没有写“禁止用基本几何体拼凑”这条通用底线")
    md = re.search(r"约\s*([\d.]+)\s*秒", first)
    dur = float(md.group(1)) if md else None
    if dur is None:
        err("开头没有写时长")
    elif not 8 <= dur <= 15.6:
        err(f"时长 {dur} 秒超出 8–15.6 秒")
    res = set(re.findall(r"(\d{3,4})×(\d{3,4})", topic))
    fps = set(re.findall(r"(\d+)\s*帧/秒", topic))
    if len(res) != 1 or len(fps) != 1:
        err(f"分辨率或帧率不一致或缺失：{res or '无'} / {fps or '无'}")
    mf = re.search(r"共\s*(\d+)\s*帧", topic)
    if mf and dur and len(fps) == 1 and int(mf.group(1)) != round(dur * int(next(iter(fps)))):
        err(f"总帧数 {mf.group(1)} 和时长×帧率不一致")
    if "无声音" not in topic:
        warn("没有写“无声音”")
    if "重点效果要求如下" not in topic:
        err("缺少“重点效果要求如下：”")
    segs = re.findall(r"第\s*([\d.]+)–([\d.]+)\s*秒", topic)
    if not segs:
        err("剧本正文缺少“第 X–Y 秒”的分段")
    elif dur and abs(float(segs[-1][1]) - dur) > 0.5:
        warn(f"最后一段结束于 {segs[-1][1]} 秒，和时长 {dur} 秒不一致")
    if not re.search(r"结束[。]?", topic.split("以下是")[-1]):
        warn("剧本正文没有写画面在什么时刻结束")
    for pat, label in ((r"考点|考题|考察", "“考点/考题/考察”字样"), (r"\bL[1-4]\b", "L1–L4 分级"),
                       (r"题目档位|基准档|进阶档|上限档", "题目档位"), (r"耦合链", "耦合链"),
                       (r"\*\*类目\*\*", "类目")):
        mm = re.search(pat, t)
        if mm:
            err(f"文件里出现了{label}：“{mm.group(0)}”（考点、分级、档位和类目只在回复中说明）")
    if re.search(r"^## 考点", t, re.M):
        err("文件里不应有“## 考点”一节")
    check_tp_file(path)
    report()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    brief_path = args[0]
    tax_path = None
    if "--taxonomy" in args:
        tax_path = args[args.index("--taxonomy") + 1]
    base = os.path.basename(brief_path)
    if not base.endswith("_制作需求.md"):
        for suffix, label in (("剧本.md", "剧本文件"), ("考点说明.md", "考点说明文件")):
            main_path = os.path.join(os.path.dirname(brief_path), base[:-len(suffix)] + ".md")
            if base.endswith(suffix) and os.path.exists(main_path):
                warn(f"请检查主文件（<标题>.md），{label}会随主文件一起核对")
                brief_path = main_path
                break
        if base == "rubric.json":
            mains = [f for f in os.listdir(os.path.dirname(brief_path) or ".")
                     if f.endswith(".md") and not f.endswith(("剧本.md", "考点说明.md"))]
            if len(mains) == 1:
                warn("请检查主文件（<标题>.md），rubric.json 会随主文件一起核对")
                brief_path = os.path.join(os.path.dirname(brief_path), mains[0])
        head = open(brief_path, encoding="utf-8-sig", errors="ignore").read()
        if "## 场景和主体" in head:
            check_v3(brief_path)
        else:
            check_single(brief_path, tax_path)
        return
    if not base.endswith("_制作需求.md"):
        err("制作需求文件名应为 <标题>_制作需求.md")
    title = base.replace("_制作需求.md", "")
    script_path = os.path.join(os.path.dirname(brief_path), f"{title}剧本.md")
    if not os.path.exists(script_path):
        err(f"找不到剧本 {title}剧本.md（剧本文件名不能带版本号）")
        report(); return
    if re.search(r"(v\d|版本|新版|修订|_\d+$)", title, re.I):
        err("标题里带有版本号")

    b = read(brief_path)
    s = read(script_path)

    # ---------- Prompt
    if "```text" not in b:
        err("制作需求里没有 ```text 代码块形式的 Prompt")
        report(); return
    p = b.split("```text", 1)[1].split("```", 1)[0].strip()
    if not p.startswith("使用 Blender 5.0.0"):
        err("Prompt 没有以“使用 Blender 5.0.0”开头")
    for pat, label in ((r"bpy|\bAPI\b|Python|python|(?<!色彩)脚本|代码|函数", "代码或编程相关的词"),
                       (r"\b[a-z]+_[a-z_]+\b", "像属性变量名的英文"),
                       (r"\b[a-z]+\.[a-z_]+\(", "像函数调用的写法"),
                       (r"`", "代码格式的反引号")):
        m = re.search(pat, p)
        if m:
            err(f"Prompt 里出现了{label}：“{m.group(0)}”（提示词不能包含代码、API 或属性名）")
    if f"《{title}剧本》" not in p:
        err(f"Prompt 里没有引用《{title}剧本》")
    m = re.search(r"约\s*([\d.]+)\s*秒", p)
    if not m:
        err("Prompt 开头没有写时长")
    else:
        dur = float(m.group(1))
        if dur < 8 or dur > 15.6:
            err(f"时长 {dur} 秒超出 8–15.6 秒")
        elif dur > 12:
            warn(f"时长 {dur} 秒超过默认的 12 秒，需确认用户已同意")
    if "不得少于 8 秒" not in p:
        warn("Prompt 没有写“不得少于 8 秒”")
    for k in ("核心效果：", "不可改变的内容：", "可调整范围：", "禁止：", "输出规格："):
        if k not in p:
            err(f"Prompt 缺少“{k}”段")
    if "质感要求：" not in p:
        warn("Prompt 没有“质感要求：”段（旧任务格式；新任务必须有）")
    if b.count("制作时同时提供") != 1 or b.find("制作时同时提供") > 200:
        warn("“制作时同时提供……”应只在文件开头出现一次")

    # ---------- resolution / fps consistency
    def spec(text, label):
        r = re.search(r"(\d{3,4})×(\d{3,4})", text)
        f = re.search(r"(\d+)\s*帧/秒", text)
        if not r or not f:
            err(f"{label} 没有写分辨率或帧率")
            return None
        return (r.group(1), r.group(2), f.group(1))
    acc_text = section(b, "## 四、试做验收要点", "## 五、")
    s_basic = section(s, "## 基本设定", "## ")
    specs = {"剧本「基本设定」": spec(s_basic, "剧本「基本设定」"),
             "Prompt「输出规格」": spec(section(p, "输出规格："), "Prompt「输出规格」"),
             "验收表": spec(acc_text, "验收表")}
    vals = {v for v in specs.values() if v}
    if len(vals) > 1:
        err("三处分辨率/帧率不一致：" + "；".join(f"{k}={v}" for k, v in specs.items()))
    out_spec = find_up(os.path.dirname(brief_path), ".kiro/steering/animation-output-spec.md")
    if out_spec and vals:
        o = open(out_spec, encoding="utf-8-sig").read()
        orr = re.search(r"(\d{3,4})×(\d{3,4})", o); ofr = re.search(r"(\d+)\s*帧/秒", o)
        if orr and ofr and (orr.group(1), orr.group(2), ofr.group(1)) not in vals:
            warn("分辨率/帧率与 animation-output-spec.md 的默认值不同（旧任务可以忽略）")

    # ---------- script hygiene
    for w in ("验收", "类目", "选定标签", "主行为"):
        if w in s:
            warn(f"剧本里出现“{w}”，剧本只应写画面内容")
    if "无声音" not in s_basic:
        warn("剧本「基本设定」没有写“无声音”")

    # ---------- test points (section 5)
    tp_path = find_up(os.path.dirname(brief_path), ".kiro/steering/animation-test-points.md") \
        or os.path.join(HERE, "..", "references", "test-points.md")
    sec5 = section(b, "## 五、考点与分级")
    if not sec5:
        warn("没有「五、考点与分级」一节（旧任务可以忽略；新任务必须有）")
    elif os.path.exists(tp_path):
        tp = {}
        for r in table_rows(section(open(tp_path, encoding="utf-8-sig").read(), "## 考点表", "## 档位配方")):
            if len(r) >= 4 and r[0].isdigit():
                tp[r[0]] = (r[2], r[3])
        trs = [r for r in table_rows(sec5) if r and r[0].isdigit()]
        if not trs:
            err("「五、考点与分级」里没有考点")
        grades = []
        for r in trs:
            if len(r) < 5:
                err(f"考点行应有 5 列：{r}"); continue
            if r[0] not in tp:
                err(f"考点编号 {r[0]} 不在考点表中"); continue
            name, g = tp[r[0]]
            if r[1] != name:
                err(f"考点 {r[0]} 的名称应为“{name}”，现在是“{r[1]}”")
            if r[2] != g:
                err(f"考点 {r[0]} 的分级应为 {g}，现在是 {r[2]}")
            grades.append(g)
        mt = re.search(r"\*\*题目档位\*\*[：:]\s*(基准档|进阶档|上限档)", sec5)
        if not mt:
            err("「五、考点与分级」缺少“题目档位”（基准档/进阶档/上限档）")
        elif grades:
            ok, why = recipe_ok(mt.group(1), grades)
            if not ok:
                err(f"考点组合不符合{mt.group(1)}的配方：{why}")
        if "**耦合链**" not in sec5:
            err("「五、考点与分级」缺少“耦合链”说明")
        mg = re.search(r"\*\*最高分级\*\*[：:]\s*(L\d)", sec5)
        if not mg:
            err("「五、考点与分级」缺少“最高分级”")
        elif grades and mg.group(1) != max(grades):
            err(f"最高分级应为 {max(grades)}，现在写的是 {mg.group(1)}")
        if "「五、考点与分级」" not in b.split("---", 1)[0]:
            warn("文件开头的说明没有写明「五、考点与分级」不属于制作输入")

    # ---------- acceptance quotes
    rows = table_rows(acc_text)
    if not rows or rows[0][:4] != ["来源", "要求原文", "通过时应看到的表现", "检查位置或方法"]:
        err("验收表的表头应为：来源｜要求原文｜通过时应看到的表现｜检查位置或方法")
    rows = rows[1:]
    quotes = []
    for i, r in enumerate(rows, 1):
        if len(r) != 4:
            err(f"验收表第 {i} 行不是 4 列"); continue
        src, q = r[0], r[1]
        quotes.append(q)
        if src == "Prompt":
            if q not in p:
                err(f"验收第 {i} 行原文不在 Prompt 中：{q}")
        elif src.startswith(f"《{title}剧本》"):
            if q not in s:
                err(f"验收第 {i} 行原文不在剧本中：{q}")
        else:
            err(f"验收第 {i} 行来源应为 Prompt 或《{title}剧本》+段落名：{src}")
        if q.startswith("禁止"):
            warn(f"验收第 {i} 行原文带了“禁止”前缀")
    if len(rows) < 20:
        warn(f"验收表只有 {len(rows)} 行，可能覆盖不全")

    def covered(item):
        item = item.strip().rstrip("。")
        if "剪辑" in item and any("连续镜头" in q or "剪辑" in q for q in quotes):
            return True
        return any(q in item or item in q for q in quotes)
    for name in ("不可改变的内容：", "禁止："):
        seg = section(p, name).split("\n\n", 1)[0]
        for it in [x for x in re.split(r"[；;]", seg) if x.strip()]:
            if not covered(it):
                warn(f"{name[:-1]}中的“{it.strip()[:40]}”没有对应的验收行")
    qual = section(p, "质感要求：", "不可改变的内容：")
    for line in qual.splitlines():
        line = line.strip()
        if line.startswith("- "):
            body = line[2:].split("：", 1)[-1]
            if not any(q in body for q in quotes):
                warn(f"质感要求“{line[2:22]}…”没有任何验收行引用")
    if not any("16:9" in q for q in quotes):
        err("验收表缺少输出规格一行")
    if not any(re.search(r"约\s*[\d.]+\s*秒", q) for q in quotes):
        err("验收表缺少时长一行")

    # ---------- taxonomy
    if not tax_path:
        tax_path = find_up(os.path.dirname(brief_path), ".kiro/steering/animation-taxonomy.md") \
            or os.path.join(HERE, "..", "references", "animation-taxonomy.md")
    if not os.path.exists(tax_path):
        warn("找不到分类表，跳过类目和标签检查")
        report(); return
    cats, tags, behaviors = load_taxonomy(tax_path)
    sec3 = section(b, "## 三、类目与标签", "## 四、")
    mc = re.search(r"\*\*主类目\*\*[：:]\s*(\S+)", sec3)
    if not mc:
        err("没有写主类目")
    elif mc.group(1) not in cats:
        err(f"主类目“{mc.group(1)}”不在分类表中")
    if "归类理由" not in sec3:
        err("没有写归类理由")
    trows = table_rows(sec3)
    if not trows or trows[0][:3] != ["标签组", "选定标签", "必要说明"]:
        err("标签表的表头应为：标签组｜选定标签｜必要说明")
    seen, n_beh, n_main = set(), 0, 0
    for r in trows[1:]:
        if len(r) < 2:
            continue
        g, v = r[0], r[1]
        seen.add(g)
        if g not in ALL_GROUPS:
            err(f"未知的标签组“{g}”"); continue
        if v.startswith("不填") or v == "":
            if g in REQUIRED:
                err(f"必填标签组“{g}”没有填写")
            continue
        if g == "动画行为":
            n_beh += 1
            is_main = v.startswith("主行为")
            n_main += is_main
            path = re.sub(r"^(主行为|辅助行为)[：:]", "", v).strip()
            parts = tuple(x.strip() for x in path.split("/"))
            if len(parts) != 3 or parts not in behaviors:
                err(f"动画行为“{path}”不在分类表中（应写成 大类/行为类/标签名）")
            elif is_main and parts[0] not in MAIN_OK:
                err(f"主行为“{path}”的大类不能作为主行为")
            continue
        names = [re.sub(r"[（(].*?[）)]", "", x).strip() for x in re.split(r"[、,，]", v) if x.strip()]
        for n in names:
            if n not in tags.get(g, set()):
                err(f"标签组“{g}”里没有“{n}”")
        if g in SINGLE and len(names) != 1:
            err(f"标签组“{g}”只能单选，现在有 {len(names)} 个")
        if g == "材质质感" and not 1 <= len(names) <= 3:
            err("材质质感应为 1–3 个")
        if g == "应用场景" and len(names) > 2:
            err("应用场景最多 2 个")
    for g in ALL_GROUPS - seen:
        err(f"标签表缺少“{g}”这一组")
    if not 1 <= n_beh <= 4:
        err(f"动画行为应为 1–4 个，现在有 {n_beh} 个")
    if n_main != 1:
        err(f"必须有且只有 1 个主行为，现在有 {n_main} 个")
    report()


def report():
    for m in ERR:
        print("ERROR", m)
    for m in WARN:
        print("WARN ", m)
    print(f"结果：{len(ERR)} 个 ERROR，{len(WARN)} 个 WARN")
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
