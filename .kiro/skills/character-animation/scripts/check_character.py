#!/usr/bin/env python3
"""人物动画 skill 的检查脚本（人物版 1.0）。

先按 animation-brief-advanced 1.6 的全部规则检查（换上人物类目、人物制作底线和人物基调），再查人物部分。

用法：python3 check_character.py <任务文件夹>/<标题>.md
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "references")
ADV = os.path.join(HERE, "..", "..", "animation-brief-advanced", "scripts", "check_brief.py")
if not os.path.exists(ADV):
    print("找不到 animation-brief-advanced/scripts/check_brief.py：两个 skill 要放在同一个 skills 目录下")
    sys.exit(2)
_spec = importlib.util.spec_from_file_location("check_brief", ADV)
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

CHAR_TAX = os.path.join(REF, "character-taxonomy.md")
CHAR_BASE = os.path.join(REF, "character-baseline.md")
CHAR_TONES = os.path.join(REF, "character-tones.md")

# ---------- 让进阶版的检查认得人物类目、人物底线和人物基调
_orig_tax = cb.load_taxonomy
_orig_base = cb.load_baseline
_orig_tones = cb.load_tones


def load_taxonomy(path):
    cats, tags, beh = _orig_tax(path)
    extra, _, _ = _orig_tax(CHAR_TAX)
    return cats | extra, tags, beh


def load_baseline(path):
    rows, mods = _orig_base(path)
    r2, m2 = _orig_base(CHAR_BASE)
    rows.update(r2)
    mods.update(m2)
    return rows, mods


def load_tones(folder):
    out = _orig_tones(folder) or {}
    rows = cb.table_rows(open(CHAR_TONES, encoding="utf-8-sig").read())
    head = rows[0]
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        g = lambda k: next((r[i] for i, h in enumerate(head) if h.startswith(k)), "")
        out[r[0]] = {"ratio": cb._range(g("主辅光比")), "focal": cb._range(g("焦距")),
                     "looks": [x.strip() for x in re.split(r"[、,，]", g("AgX 观感")) if x.strip()]}
    return out


cb.load_taxonomy = load_taxonomy
cb.load_baseline = load_baseline
cb.load_tones = load_tones

_orig_report = cb.report
MAIN = {"path": None}

err, warn = cb.err, cb.warn
CARD_ITEMS = ["年龄段", "身高和头身比", "体型", "脸型特征", "发型发色", "服装和材质", "性格", "原创说明"]
EYE = r"角膜缘|角膜|虹膜|眼睑|泪线|泪阜|眼白|睫毛"
FACE = r"眉弓|颧骨|鼻梁|下颌|鼻唇沟|颊脂|人中|下巴"
AU_WORDS = r"眉头内侧上抬|眉尾上抬|皱眉|眯眼|睁大|脸颊上提|嘴角上扬|嘴角下拉|抿嘴|皱鼻|上唇上提|下巴上推|嘴角往两侧"
UNCANNY = [r"湿润|反光", r"焦点", r"眨眼", r"次表面散射", r"牙齿|牙龈", r"眼轮匝肌", r"不对称", r"呼吸", r"发际线", r"胸锁乳突肌|脖子"]
CHAR_DIMS = ["形体与解剖", "面部与表情", "表演与动作"]


def _sec(t, a, b=None):
    return cb.section(t, a, b)


def char_checks(path):
    folder = os.path.dirname(path)
    title = os.path.basename(path)[:-3]
    t = open(path, encoding="utf-8-sig").read()
    tp_path = os.path.join(folder, f"{title}考点说明.md")
    tp = open(tp_path, encoding="utf-8-sig").read() if os.path.exists(tp_path) else ""
    e0, w0 = len(cb.ERR), len(cb.WARN)
    pos = cb._neg_free(t)

    # 考点说明：人物规范、路线、类目、角色设定卡
    if not re.search(r"\*\*人物规范\*\*[：:]\s*人物版\s*\d+\.\d+", tp):
        err("考点说明缺少“**人物规范**：人物版 1.0”")
    mr = re.search(r"\*\*路线\*\*[：:]\s*(写实|风格化)", tp)
    route = mr.group(1) if mr else ""
    if not route:
        err("考点说明缺少“**路线**：写实”或“**路线**：风格化”")
    mc = re.search(r"\*\*主类目\*\*[：:]\s*(\S+)", tp)
    cat = mc.group(1) if mc else ""
    if route and not cat.startswith(f"角色动画/{route}人物"):
        err(f"路线是{route}，主类目应在“角色动画/{route}人物/…”下（见 references/character-taxonomy.md）")
    look = cb._tag(tp, "视觉造型")
    if route == "写实" and look and look != "写实":
        err(f"路线是写实，视觉造型标签却是“{look}”")
    if route == "风格化" and look == "写实":
        err("路线是风格化，视觉造型标签不能是“写实”（用卡通或半写实）")
    card = _sec(tp, "## 角色设定卡", "## ")
    if not card:
        err("考点说明缺少“## 角色设定卡”")
    else:
        miss = [k for k in CARD_ITEMS if k not in card]
        if miss:
            err(f"角色设定卡缺少：{'、'.join(miss)}")

    scene = _sec(t, "## 场景和主体", "## 动作和镜头")
    act = _sec(t, "## 动作和镜头", "## 关键效果和做法")

    # 原创和动作数据
    if not (re.search(r"原创", scene) and re.search(r"不像|不参照|不照搬", t)):
        err("“场景和主体”要写明人物是原创的，并写一句不像任何真人或已有作品里的角色")
    m = re.search(r"动作捕捉|动捕|面部捕捉|面捕|mocap|Mixamo|动作库", pos, re.I)
    if m:
        err(f"正文正面写了“{m.group(0)}”：本 skill 不用外部动作数据，动作和表情用关键帧、骨骼和形态键做")

    # 形体比例
    if not re.search(r"\d+(?:\.\d+)?\s*(?:–\s*\d+(?:\.\d+)?\s*)?个头", scene):
        err("“场景和主体”没写头身比（例如“约 7 个头”，见 references/anatomy-proportions.md）")
    if not re.search(r"(?:身高|高约|个子)[^。]{0,8}\d+\s*(?:厘米|米)", scene):
        err("“场景和主体”没写身高（带单位）")
    if not re.search(r"灰模[^。]{0,40}(?:比例格|头高|侧面|正面)", t):
        err("灰模自查要包括人物比例（正面、侧面加比例格，见 references/anatomy-proportions.md）")

    # 面部
    if len(set(re.findall(EYE, t))) < 3:
        err("眼睛写得不够：角膜、虹膜、眼睑厚度、泪线、泪阜、睫毛里至少写三样")
    if len(set(re.findall(FACE, scene))) < 2:
        err("面部骨相和软组织写得不够：眉弓、颧骨、鼻梁、下颌、鼻唇沟、颊脂垫里至少写两样")

    # 表情
    if not (re.search(r"动作单元|AU\d", t) or len(set(re.findall(AU_WORDS, t))) >= 3):
        err("表情没有按面部动作单元写（例如“眉头内侧上抬加嘴角下拉”，见 references/face-expression.md）")
    if not re.search(r"不对称|一边嘴角|一侧嘴角|一边眉", t):
        err("表情没写左右不对称")
    if not re.search(r"眉眼先|眼睛先|眉先|眼先|先动[^。]{0,10}嘴|嘴后动", t):
        err("表情没写先后（眉眼先动、嘴后动）")
    if re.search(r"笑", act) and route == "写实" and "眼轮匝肌" not in t:
        err("写实人物笑的时候要写眼轮匝肌收缩（只动嘴角是假笑）")

    # 皮肤、头发、服装
    if route == "写实":
        for k, msg in ((r"次表面散射", "次表面散射"), (r"毛孔", "毛孔分区"), (r"高光[^。]{0,12}(?:碎|打碎|油)|T 区|油亮", "高光的碎变化")):
            if not re.search(k, t):
                err(f"写实皮肤缺少{msg}（见 references/skin-hair-cloth.md）")
        hits = sum(1 for p in UNCANNY if re.search(p, t))
        if hits < 6:
            err(f"恐怖谷清单只落实了 {hits} 条，写实路线至少写进 6 条（见 references/style-routes.md 第三节）")
    if route == "风格化":
        m = re.search(r"毛孔|照片贴图的皮肤|皮肤照片", pos)
        if m:
            err(f"风格化路线正面写了“{m.group(0)}”：风格化比例配写实皮肤是禁配（见 references/style-routes.md）")
    if re.search(r"头发|发型|发丝|辫|发梢", scene):
        if "曲线毛发" not in t:
            err("头发没写做法（用曲线毛发：引导毛、成簇、碎发）")
        if not re.search(r"发际线", t):
            warn("头发没写发际线的过渡（稀疏的短碎发，不是一条硬边）")
    if re.search(r"裙|外套|围巾|斗篷|衣角|长袍|褂|衫", t) and not re.search(r"布料模拟|修正形态键", t):
        err("写了服装，但没写服装怎么动（布料模拟以身体为碰撞体，或贴身部分跟骨骼加修正形态键）")

    # 表演和动作
    for k, msg in ((r"预备", "预备动作"), (r"重心", "重心"), (r"跟随|余摆|滞后", "跟随和余摆"),
                   (r"视线|眼神|眼睛先", "视线")):
        if not re.search(k, act + _sec(t, "## 关键效果和做法", "## 灯光和画面")):
            err(f"表演缺少{msg}（见 references/performance-motion.md）")
    if not re.search(r"呼吸", t):
        warn("没写呼吸：静止时胸口和肩也跟着呼吸起伏")
    if re.search(r"拿|握|抓|捏|递|接过|端起|扶", act) and not re.search(r"手指|指腹|指尖|指节", t):
        err("有手拿东西的动作，但没写手指和指腹怎么贴住物体")
    if not re.search(r"(?:近景|特写)[^。]{0,60}(?:脸|面部|眼睛)|(?:脸|面部)[^。]{0,30}(?:占|画面高度)", act):
        warn("表情的关键时刻没有一段近景或特写，或没写脸在画面里多大")

    # rubric 的人物关键项
    rp = os.path.join(folder, "rubric.json")
    if os.path.exists(rp):
        try:
            crit = json.loads(open(rp, encoding="utf-8").read())["criteria"]
            dims = {c["dimension"]: c for c in crit}
            for d in CHAR_DIMS:
                if d not in dims:
                    err(f"rubric 缺少人物关键项“{d}”（见 references/character-rubric.md）")
                elif not dims[d].get("critical"):
                    err(f"rubric 的“{d}”应为关键项")
        except Exception as ex:
            err(f"rubric.json 读不出来：{ex}")

    cb.ERR[e0:] = [f"人物：{m}" for m in cb.ERR[e0:]]
    cb.WARN[w0:] = [f"人物：{m}" for m in cb.WARN[w0:]]


def report():
    if MAIN["path"] and MAIN["path"].endswith(".md") and os.path.exists(MAIN["path"]):
        char_checks(MAIN["path"])
    _orig_report()


cb.report = report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    MAIN["path"] = sys.argv[1]
    cb.main()
