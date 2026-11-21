#!/usr/bin/env python3
"""检查一个动画任务是否符合 animation-brief 规则。

新格式：主文件 <标题>.md，同时核对 <标题>剧本.md 和 <标题>考点说明.md（含档位下限：默认至少进阶档）。
旧格式：<标题>_制作需求.md 和对应剧本。

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


def check_tp_file(main_path):
    """检查和主文件同目录的 <标题>考点说明.md（内部校验用，不交给制作方）。"""
    folder = os.path.dirname(main_path)
    title = os.path.basename(main_path)[:-3]
    name = f"{title}考点说明.md"
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        warn(f"缺少考点说明文件 {name}（已有任务可以忽略；新任务必须有）")
        return
    tp_path = find_up(folder, ".kiro/steering/animation-test-points.md") \
        or os.path.join(HERE, "..", "references", "test-points.md")
    if not os.path.exists(tp_path):
        warn("找不到考点表，跳过考点说明检查")
        return
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
    ERR[e0:] = [f"{name}：{m}" for m in ERR[e0:]]
    WARN[w0:] = [f"{name}：{m}" for m in WARN[w0:]]


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
    for pat, label in ((r"bpy|\bAPI\b|Python|python|脚本|代码|函数", "代码或编程相关的词"),
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
    for pat, label in ((r"bpy|\bAPI\b|Python|python|脚本|代码|函数", "代码或编程相关的词"),
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
