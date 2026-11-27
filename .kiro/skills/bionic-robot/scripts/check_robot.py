#!/usr/bin/env python3
"""仿生机器人 skill 的检查脚本（机器人版 1.0）。

先按 animation-brief-advanced 1.8 的全部规则检查（换上机器人类目、机器人制作底线，以及人物和机器人的基调），再查机器人部分。

用法：python3 check_robot.py <任务文件夹>/<标题>.md
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "references")
SKILLS = os.path.join(HERE, "..", "..")
ADV = os.path.join(SKILLS, "animation-brief-advanced", "scripts", "check_brief.py")
CHAR_TONES = os.path.join(SKILLS, "character-animation", "references", "character-tones.md")
if not os.path.exists(ADV):
    print("找不到 animation-brief-advanced/scripts/check_brief.py：几个 skill 要放在同一个 skills 目录下")
    sys.exit(2)
_spec = importlib.util.spec_from_file_location("check_brief", ADV)
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

ROBOT_TAX = os.path.join(REF, "robot-taxonomy.md")
ROBOT_BASE = os.path.join(REF, "robot-baseline.md")
ROBOT_TONES = os.path.join(REF, "robot-tones.md")

_orig_tax, _orig_base, _orig_tones = cb.load_taxonomy, cb.load_baseline, cb.load_tones


def load_taxonomy(path):
    cats, tags, beh = _orig_tax(path)
    extra, _, _ = _orig_tax(ROBOT_TAX)
    return cats | extra, tags, beh


def load_baseline(path):
    rows, mods = _orig_base(path)
    r2, m2 = _orig_base(ROBOT_BASE)
    rows.update(r2)
    mods.update(m2)
    return rows, mods


def _tones_from(path, out):
    if not os.path.exists(path):
        return
    rows = cb.table_rows(open(path, encoding="utf-8-sig").read())
    head = rows[0]
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        g = lambda k: next((r[i] for i, h in enumerate(head) if h.startswith(k)), "")
        out[r[0]] = {"ratio": cb._range(g("主辅光比")), "focal": cb._range(g("焦距")),
                     "looks": [x.strip() for x in re.split(r"[、,，]", g("AgX 观感")) if x.strip()]}


def load_tones(folder):
    out = _orig_tones(folder) or {}
    _tones_from(CHAR_TONES, out)
    _tones_from(ROBOT_TONES, out)
    return out


cb.load_taxonomy, cb.load_baseline, cb.load_tones = load_taxonomy, load_baseline, load_tones

err, warn = cb.err, cb.warn
MAIN = {"path": None}
CARD_ITEMS = ["原型", "尺寸和比例", "外观路线", "主要材料", "驱动方式", "自由度", "原创说明"]
KNOWN = (r"Atlas|Optimus|Spot|Sophia|Ameca|ASIMO|Pepper|Digit|Figure 0\d|Unitree|宇树|波士顿动力|擎天柱|阿特拉斯|"
         r"终结者|T-800|瓦力|WALL-E|伊娃|大白|高达|EVA|变形金刚|阿童木|哆啦A梦|机器猫|C-3PO|R2-D2|BB-8|钢铁侠|"
         r"Ex Machina|底特律|Detroit|西部世界|赛博坦")
DRIVES = r"无刷电机|电机|减速器|推杆|丝杠|液压缸|人工肌肉|钢丝绳|同步带|连杆|舵机"


def _sec(t, a, b=None):
    return cb.section(t, a, b)


def robot_checks(path):
    folder = os.path.dirname(path)
    title = os.path.basename(path)[:-3]
    t = open(path, encoding="utf-8-sig").read()
    tp_path = os.path.join(folder, f"{title}考点说明.md")
    tp = open(tp_path, encoding="utf-8-sig").read() if os.path.exists(tp_path) else ""
    e0, w0 = len(cb.ERR), len(cb.WARN)
    pos = cb._neg_free(t)
    scene = _sec(t, "## 场景和主体", "## 动作和镜头")
    act = _sec(t, "## 动作和镜头", "## 关键效果和做法")
    eff = _sec(t, "## 关键效果和做法", "## 灯光和画面")

    # 考点说明
    if not re.search(r"\*\*机器人规范\*\*[：:]\s*机器人版\s*\d+\.\d+", tp):
        err("考点说明缺少“**机器人规范**：机器人版 1.0”")
    mp = re.search(r"\*\*原型\*\*[：:]\s*(\S+)", tp)
    if not mp:
        err("考点说明缺少“**原型**：<物种>”")
    ml = re.search(r"\*\*外观\*\*[：:]\s*(工业写实|消费电子白壳)", tp)
    if not ml:
        err("考点说明缺少“**外观**：工业写实”或“**外观**：消费电子白壳”")
    cat = (re.search(r"\*\*主类目\*\*[：:]\s*(\S+)", tp) or [None, ""])[1]
    if not cat.startswith("角色动画/仿生机器人/"):
        err("主类目应在“角色动画/仿生机器人/…”下（见 references/robot-taxonomy.md）")
    humanoid = cat.endswith("人形机器人")
    face = re.search(r"\*\*面部路线\*\*[：:]\s*(无脸面罩|机械脸|仿生脸)", tp)
    if humanoid and not face:
        err("人形机器人的考点说明要写“**面部路线**：无脸面罩、机械脸或仿生脸”")
    card = _sec(tp, "## 机器人设定卡", "## ")
    if not card:
        err("考点说明缺少“## 机器人设定卡”")
    else:
        miss = [k for k in CARD_ITEMS if k not in card]
        if miss:
            err(f"机器人设定卡缺少：{'、'.join(miss)}")

    # 原型和原创
    if not re.search(r"原型", scene):
        err("“场景和主体”要写明机器人的原型（以什么动物或人为原型、借了哪些结构）")
    if not (re.search(r"原创", scene) and re.search(r"不像|不参照|不照搬", t)):
        err("“场景和主体”要写明机器人是原创的，并写一句不像任何现有机器人")
    m = re.search(KNOWN, pos)
    if m:
        err(f"正文出现了现有机器人或作品的名字：“{m.group(0)}”，机器人要原创，不写品牌、型号和作品名")
    if re.search(r"动作捕捉|动捕|面部捕捉|mocap|Mixamo", pos, re.I):
        err("本 skill 不用外部动作数据")

    # 比例、自由度、驱动、外壳
    if humanoid and not re.search(r"\d+(?:\.\d+)?\s*个头", scene):
        err("人形机器人没写头身比（例如“约 7.5 个头”）")
    if not re.search(r"身高|体长|肩高|翼展|全长", scene):
        err("没写机器人的尺寸（身高、体长、肩高或翼展）")
    if not re.search(r"\d+\s*个自由度|自由度", t):
        err("没写关节的自由度（见 references/bio-mech-mapping.md）")
    if len(re.findall(r"\d+\s*°|\d+\s*度", t)) < 3:
        err("关节转动范围写得不够：至少写三处带度数的转动范围")
    if len(set(re.findall(DRIVES, t))) < 2:
        err("没写清驱动方式（电机加减速器、推杆、液压缸、钢丝绳、同步带、连杆里至少两种）")
    if not re.search(r"(?:间隙|缝)[^。]{0,12}\d+(?:–\d+)?\s*毫米|\d+(?:–\d+)?\s*毫米[^。]{0,8}(?:间隙|的缝)", t):
        err("没写外壳的分缝或关节处的间隙（带毫米）")
    if not re.search(r"旋转限制约束|限制旋转约束", t):
        err("没写旋转限制约束（每个关节的转动范围）")
    if not re.search(r"父子级", t):
        err("没写刚性零件用父子级绑定")
    if not re.search(r"质心|重心", act + eff):
        err("没写平衡：质心或重心在支撑面内")
    if not re.search(r"过冲|伺服", t):
        err("没写电机的动作特性（到位的极小过冲、静止时的伺服修正）")
    if not re.search(r"线缆|护套|管", t):
        warn("没写线缆、护套或管路：跨关节处的弯曲余量和余摆")

    # 人形的手和面部
    if humanoid:
        if not (re.search(r"手指|指节", t) and re.search(r"拇指", t) and re.search(r"指腹", t)):
            err("人形机器人的手要写手指分节、拇指对掌和指腹（橡胶垫）")
        if face and face.group(1) == "仿生脸" and not re.search(r"动作单元|AU\d", t):
            err("仿生脸要按面部动作单元写驱动点（见人物 skill 的 face-expression.md）")
        if not re.search(r"视线|摄像头|镜头模组", scene + act):
            err("人形机器人要写眼睛（摄像头）的位置和视线")

    # 外观路线不混
    if ml and ml.group(1) == "消费电子白壳" and re.search(r"油管|液压管|裸露的线缆", pos):
        warn("消费电子白壳路线里出现了外露的油管或线缆，确认没有混进工业写实")

    # rubric
    rp = os.path.join(folder, "rubric.json")
    if os.path.exists(rp):
        try:
            dims = {c["dimension"]: c for c in json.loads(open(rp, encoding="utf-8").read())["criteria"]}
            need = ["仿生原型与比例", "机械结构与运动学"] + (["面部与表演"] if humanoid else [])
            for d in need:
                if d not in dims:
                    err(f"rubric 缺少机器人关键项“{d}”（见 references/robot-rubric.md）")
                elif not dims[d].get("critical"):
                    err(f"rubric 的“{d}”应为关键项")
        except Exception as ex:
            err(f"rubric.json 读不出来：{ex}")

    cb.ERR[e0:] = [f"机器人：{m}" for m in cb.ERR[e0:]]
    cb.WARN[w0:] = [f"机器人：{m}" for m in cb.WARN[w0:]]


_orig_report = cb.report


def report():
    if MAIN["path"] and MAIN["path"].endswith(".md") and os.path.exists(MAIN["path"]):
        robot_checks(MAIN["path"])
    _orig_report()


cb.report = report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    MAIN["path"] = sys.argv[1]
    cb.main()
