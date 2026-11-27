# 可参考的开源项目（人物版 1.0，2026 年 11 月核对）

| 方面 | 项目 | 许可 | 能参考什么 | 在本 skill 里怎么用 |
|---|---|---|---|---|
| 身形比例 | MPFB2（MakeHuman 的 Blender 扩展），https://github.com/makehumancommunity/mpfb2 | 代码 GPL，资产 CC0 | 按年龄、性别、肌肉、体重等参数生成人体，带骨骼和面部形态键 | 允许用它生成人体当起形的底子，再重新雕刻；附带的皮肤、眼睛、头发、衣服和姿势预设不用 |
| 身形和拓扑 | Blender 官方 Human Base Meshes（Blender 官网 Demo Files 页下载） | CC0 | 写实和风格化的人体、头部基础网格，关节和面部的环形布线 | 允许当起形的底子，再重新雕刻；也用来学布线 |
| 风格化角色流程 | Blender Studio 的 Stylized Character Workflow 教程 | 教程免费 | 风格化角色从雕刻、拓扑到绑定的流程 | 只学方法 |
| 绑定 | Rigify | Blender 内置 | 人形骨骼模板、面部骨骼、反向动力学 | 直接用 |
| 表情体系 | 面部动作编码系统（FACS）和 ARKit 的 52 个面部形态键 | 公开标准 | 把表情拆成独立的面部动作单元 | 写表情的词表和形态键命名 |
| 面部捕捉 | CaptureForge（GPL-3.0）、VIPER、Blender-Face-Animation 等基于 MediaPipe 的插件 | 开源 | 用视频驱动面部形态键 | 本项目不用外部动作数据，只参考它们怎么把 52 个形态键对到 Rigify 上 |
| 动画曲线 | AnimAide | 开源 | 调运动曲线和缓入缓出 | 直接用 |
| 次级运动 | Wiggle 2 | 开源 | 骨骼的余摆，适合头发和配饰 | 直接用 |

不在这里列的商业插件（例如 Auto-Rig Pro、Human Generator、FaceIt）一律不用，也不写进文件。
