#!/usr/bin/env python3
"""下载 Poly Haven 的 CC0 素材（贴图、模型、HDRI），供效果图使用。

用法：
  python3 fetch_polyhaven.py search <关键词> [--type textures|models|hdris]
  python3 fetch_polyhaven.py tex   <资产名> [分辨率，默认 2k]   -> <dest>/tex/<资产名>/{diff,nor,rough,disp}.jpg
  python3 fetch_polyhaven.py model <资产名> [分辨率，默认 1k]   -> <dest>/models/<资产名>/*.blend（含贴图）
  python3 fetch_polyhaven.py hdri  <资产名> [分辨率，默认 4k]   -> <dest>/hdri/<资产名>.hdr
选项：--dest <目录>，默认 ./assets

Poly Haven 要求请求带 User-Agent，本脚本已设置。所有素材均为 CC0，可免费商用。

注意：模型和 HDRI 只用于内部效果图。交给制作方的主文件只允许图像贴图，不能写进这里下载的模型和环境贴图。
"""
import json
import os
import sys
import urllib.request

UA = {"User-Agent": "kiro-mockup-fetch/1.0"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print("exists", path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url)
    with open(path, "wb") as f:
        f.write(data)
    print("saved", path, round(len(data) / 1e6, 1), "MB")


def files(asset):
    return json.loads(get("https://api.polyhaven.com/files/" + asset))


def fetch_texture(dest, asset, res="2k"):
    f = files(asset)
    for key, name in (("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough"), ("Displacement", "disp")):
        if key not in f:
            print("missing", asset, key)
            continue
        fmt = "jpg" if "jpg" in f[key][res] else "png"
        save(f[key][res][fmt]["url"], os.path.join(dest, "tex", asset, f"{name}.{fmt}"))


def fetch_model(dest, asset, res="1k"):
    b = files(asset)["blend"][res]["blend"]
    d = os.path.join(dest, "models", asset)
    save(b["url"], os.path.join(d, os.path.basename(b["url"])))
    for rel, inc in b.get("include", {}).items():
        save(inc["url"], os.path.join(d, rel))


def fetch_hdri(dest, asset, res="4k"):
    h = files(asset)["hdri"][res]["hdr"]
    save(h["url"], os.path.join(dest, "hdri", asset + ".hdr"))


def search(word, kind="textures"):
    a = json.loads(get(f"https://api.polyhaven.com/assets?t={kind}"))
    for k, v in sorted(a.items()):
        text = " ".join([k, v.get("name", "")] + v.get("categories", []) + v.get("tags", []))
        if word.lower() in text.lower():
            print(k, "|", ", ".join(v.get("categories", [])))


def main():
    args = sys.argv[1:]
    dest = "assets"
    if "--dest" in args:
        i = args.index("--dest"); dest = args[i + 1]; del args[i:i + 2]
    kind = "textures"
    if "--type" in args:
        i = args.index("--type"); kind = args[i + 1]; del args[i:i + 2]
    if len(args) < 2:
        print(__doc__); sys.exit(2)
    cmd, name, *rest = args
    if cmd == "search":
        search(name, kind)
    elif cmd == "tex":
        fetch_texture(dest, name, *(rest or ["2k"]))
    elif cmd == "model":
        fetch_model(dest, name, *(rest or ["1k"]))
    elif cmd == "hdri":
        fetch_hdri(dest, name, *(rest or ["4k"]))
    else:
        print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
