#!/usr/bin/env python3
"""检查一份动画制作需求（<标题>_制作需求.md）和对应剧本是否符合 animation-brief 规则。

用法：python3 check_brief.py <任务文件夹>/<标题>_制作需求.md [--taxonomy 路径]
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


def section(text, start, end=None):
    if start not in text:
        return ""
    s = text.split(start, 1)[1]
    if end and end in s:
        s = s.split(end, 1)[0]
    return s


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
    acc_text = section(b, "## 四、试做验收要点")
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
