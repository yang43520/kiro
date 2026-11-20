# 效果图渲染指南（Blender 5.0.0，命令行）

> 本指南只用于我们自己出内部预览效果图。项目的正式制作只允许用贴图，这里用到的 Poly Haven 模型和 HDRI 不能写进 Prompt（贴图可以）。

只在用户要求时才渲染效果图。默认出 3 张：剧本里 3 个关键时刻各 1 张，分辨率 1280×720。

## 1. 环境

- 所有文件放在一个不会被清空的工作目录里，例如 `<workspace>/.cache/`。不要放在 `/tmp`，那里的文件可能被清掉。
- 下载 Blender 5.0.0 便携版：`https://download.blender.org/release/Blender5.0/blender-5.0.0-linux-x64.tar.xz`，解压到工作目录。
- 第一次运行先自检：`./blender-5.0.0-linux-x64/blender -b --factory-startup -noaudio --python-expr "print('ok')"`。
- 如果报缺少 `.so`（常见的是 libGL、libEGL、libSM、libICE、libXxf86vm、libwayland-client）：
  - 有 root 权限时用系统包管理器安装。
  - 没有 root 权限时，下载对应的 rpm 或 deb 包，解压到 `libroot/`，运行时加上 `LD_LIBRARY_PATH=<工作目录>/libroot/usr/lib64`。
- 需要 Pillow 拼图或缩放时，可以安装到工作目录下的 `pylib/`，用 `PYTHONPATH=pylib python3` 调用。

渲染命令：

```bash
cd <工作目录> && LD_LIBRARY_PATH=<工作目录>/libroot/usr/lib64 \
  ./blender-5.0.0-linux-x64/blender -b --factory-startup -noaudio \
  --python <场景脚本>.py -- <镜头> <输出.png> <采样数> <宽度> [选项...] > <日志>.log 2>&1
```

## 2. 场景脚本的写法

- 一个任务写一个 Python 脚本，用参数切换镜头：`SHOT OUT SAMPLES RESX [flags]`。高度按 16:9 由宽度算出。
- 常用开关：`norender`（只搭场景、不渲染，用来快速查错），`exp=0.3`（调曝光）。
- 脚本开头删除默认场景里的所有对象。
- 同一个场景用"状态表"切换不同时刻：每个部件做成一个空物体加子物体，隐藏还没出现的部件；飞行中的部件给一个偏移和旋转。
- 渲染设置：

```python
scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES; scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.015; scene.cycles.use_denoising = True
scene.cycles.sample_clamp_indirect = 4.0
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
```

- Blender 5.0 的合成器要用节点组，用来加辉光（Bloom）：

```python
tree = bpy.data.node_groups.new("comp", "CompositorNodeTree")
tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
scene.compositing_node_group = tree
rl = tree.nodes.new("CompositorNodeRLayers"); gl = tree.nodes.new("CompositorNodeGlare")
gl.inputs["Type"].default_value = "Bloom"; gl.inputs["Quality"].default_value = "High"
gl.inputs["Threshold"].default_value = 1.5; gl.inputs["Strength"].default_value = 0.3
go = tree.nodes.new("NodeGroupOutput")
tree.links.new(rl.outputs["Image"], gl.inputs["Image"]); tree.links.new(gl.outputs["Image"], go.inputs[0])
scene.render.use_compositing = True
```

## 3. 迭代节奏

1. 用 `norender` 跑一遍，确认没有报错。
2. 测试图：宽 640 或 960，16–32 采样，每张大约 1 分钟。看构图、光线和明显的造型问题。
3. 终稿：宽 1280，128 采样，每张大约 4–6 分钟（8 核 CPU）。
4. 查看图片前，先把它复制成一个**新文件名**再打开，否则查看器可能显示旧图。刚写出的文件偶尔读不到，等一下重试即可。
5. 多张图可以用 Pillow 拼成一张，一次看完。
6. 只有发现明显缺陷时才重新渲染终稿。

## 4. 素材

- 用 `scripts/fetch_polyhaven.py` 搜索和下载 Poly Haven 的素材。所有素材都是 CC0，可免费商用，交付时要告诉用户。
- 贴图用 Box 投影加物体坐标，就不用展 UV；大面积地面要做防重复处理，例如用 Voronoi 给每个格子随机旋转和偏移贴图坐标。
- 植物、草、灌木优先用 Poly Haven 的模型，比程序生成的更像真的。

## 5. 写实度经验

**硬表面（机甲、车辆、机械）**

- 用"截面放样"做部件：八边形截面加一个前凸棱，沿长度方向放 3–5 个截面。
- 平直着色看起来像低面数模型；全部平滑又会显得圆鼓鼓、像卡通。正确做法是平滑着色，加 `mesh.set_sharp_from_angle(angle=22°)`，再加倒角修改器（角度限制 22°、3 段、Harden Normals）。
- 720P 下，着色器画出的面板线几乎看不见。改成真实的分层装甲片：每块主壳上叠 2 块覆盖板，中间留缝，再加螺栓和格栅，效果明显好很多。
- 金属漆：Metallic 约 0.9，底色约 0.12。用 Bevel 节点和法线的点积求出边缘遮罩，做边角磨损；用 AO 做缝隙里的脏污。
- 发光灯带要细，强度适中（Emission 约 6），否则像霓虹装饰条。

**植物**

- 树冠用空间殖民算法生长枝条，比固定规则的 L 系统自然得多。
- 不同生长阶段用同一棵树按生长步数截断，不要另做模型。

**地面**

- 干裂泥地用 Voronoi 单元做土块，共用一个抖动场，让相邻土块的边对得上。
- 远处地形的边缘要延伸到画面外并往下沉，否则会出现一条接缝线。

**暗场景**

- 只有主光时，环境会黑成一片。要加几盏场景里本来就有的小灯（检修架上的灯、壁灯），再在背景高处加一盏弱的面光，让环境的轮廓能看出来。
- 体积雾密度大约 0.005/米；太浓会让画面发灰。
- 正对镜头的轮廓光会在雾里形成很亮的光锥，需要时关掉或调暗。

**特效**

- 火花：几十根很细的发光圆柱，按初速度和重力摆出抛物线，旁边加一盏小点光源。
- 蒸汽：几个缩放后的球体，用体积材质，密度用"噪波减去阈值，再乘以离中心距离的衰减"来控制。

## 6. 交付

- 放到 `<任务文件夹>/效果图/`，命名为 `01_<时刻>.png`、`02_…`、`03_…`。
- 提交、推送，并用 `gh api` 确认文件已经在远端。
- 回复里用表格列出每张图对应剧本的哪个时刻、画面里有什么；如实写出和剧本的差距（程序化建模的细节、简化的部件、静帧看不出运动），并说明素材是 CC0。
