# 生成器 API 与范例

## 现成生成器位置

| 项目 | 生成器 | 说明 |
|------|--------|------|
| camera（A16） | `ZCode_docs/camera-porting/docs/tools/gen_html.py` | **首选参考**：含泳带 band() 支持、data/up/link 三类连线、布局自检；下表 11 个 FLOWS 全部可作范例 |
| audio（A16） | `sm6xx5_a16_um/docs/tools/gen_audio_html.py` | audio-overview"一分钟总览"多泳道样式（横向主链 + 泳道分组的对齐来源） |

新图一律在对应生成器中新增 FLOWS 定义；跨项目新写生成器时照抄该 API 与自检。

## 范例图索引（gen_html.py 中的 FLOWS）

| FLOWS 键 | 所在文档 | 版式 | 演示要点 |
|-----------|---------|------|---------|
| `arch-overview` | camera 10 §1 | 五层泳道总览 | 泳带、标题-节点 25px 间距、三平面连线、竖线绕开带标题 |
| `config-streams` | camera 10 §3.3 | 纵向 10 步 | 阶段泳带（一次/每帧）+ 右侧蓝色回传长边 |
| `control-plane-type` | camera 10 §4.1 | 横向一分二 | 分叉正交路由、分支标签 |
| `data-plane-pixels` | camera 10 §4.2 | 横向 7 节点主链 | 可选节点（note）+ 灰虚线绕行边 + 链首总线标签加宽间隙 |
| `pipeline-single` | camera 10 §5.1 | 纵向管线 | 选择头 + 串联 + 末端二分叉到 Surface |
| `pipeline-4vc` | camera 10 §5.2 | 纵向管线 | 侧挂警示节点（note+link）+ 交叉绑定分叉 |
| `overview` / `android-stack` / `config-path` / `dts-power` / `kernel-ioctl` / `chi-cdk` / `camx-config` / `tfe-yuv` / `4vc-topology` / `snapcam` | 各模块篇 | 手工坐标流程图 | 生成器原生风格（无泳带） |

## Diagram API

```python
d = Diagram("图的 aria 标题")

# 泳道带：x, y, w, h, 标题（标题基线自动在 y+23，左上角）
d.band(16, 136, 1148, 114, "Android Camera Framework（AOSP 通用）")

# 节点：id, x, y, w, 多行文字(\n 分隔), class
# 高度自动 = 行数*18+16；宽度须满足估宽+26 <= w
d.box("fw", 52, 184, 420,
      "CameraService / CameraProvider · Camera HAL3\nconfigure_streams / process_capture_request", "node")

# 锚点（端点必须用这些，禁止手算坐标）
d.top("fw", 150)      # (x+w/2+150, y)   上边
d.bottom("kern", 138) # (x+w/2+138, y+h) 下边
d.left("tfe")         # (x, y+h/2)       左边
d.right("dec")        # (x+w, y+h/2)     右边

# 连线：正交折线点列, 标签, 标签基线坐标(anchor 默认 middle)
# cls: "" 控制面 | "data" 数据面 | "up" 带外/上行 | "link" 关联无箭头
d.edge([d.bottom("fw"), (262, 268), (595, 268), d.top("camx")],
       "HAL3：configure_streams / request", (430, 263))

# 自由文字（图例/注释）
d.text(1164, 32, "灰＝控制面 · 蓝＝数据面 · 橙虚＝persist 带外",
       cls="hint", anchor="end", size=11)

d.finish(1180, 755)   # 画布尺寸
```

注册：`FLOWS["arch-overview"] = _build_arch_overview()`。

## Markdown 侧标记

```markdown
<!-- FLOWCHART: arch-overview -->
```text
（原 ASCII 图保留在此，生成器替换为 SVG 并把 ASCII 收进 <details>）
```
```

规则：标记名 = FLOWS 键名；标记必须紧跟代码块（中间只允许空行）。

## 布局节奏参考（_build_arch_overview 实测数值）

- 五条泳带 y：12 / 136 / 294 / 454 / 612（带高 104/114/140/114/120），
  间隙 20px，第 2→3、4→5 层间隙 44px（跨层连线带标签）。
- 竖线绕开带标题：`Camera2/Surface` 边从 (142,98) → (142,110) → (412,110)
  → d.top("fw",150) —— 水平段走在上方带内空白区，竖线落在标题估宽右侧。
- 长回传边（数据面）：`d.top("ope") → (992,124) → (242,124) → d.bottom("app",40)`，
  水平段走在带间间隙（y124），进入点 x 与水平段终点对齐避免斜线。
- 两条平行短箭头表双向：y 相差 38px（如 350/388），标签一上一下。
- 纵向流程图（config-streams）：节点 x=90 w=470 单列，节点间隙 30，阶段泳带
  高 = 48 + 内容 + 16；回传长边竖直段在 x700（节点右缘 540 + 60）。
- 横向主链（data-plane-pixels）：节点行 y=70 统一高度，画布 1480 宽；链首标签
  "MIPI CSI-2 YUV422" 处间隙 120px，其余 36~60px。

## 运行与验证

```bash
python3 tools/gen_html.py        # 重建全部 HTML + 自检，退出码非 0 即失败
# 渲染单图做视觉验证：
python3 - <<'EOF'
import re
text = open('html/10-xxx.html', encoding='utf-8').read()
svg = [s for s in re.findall(r'<svg.*?</svg>', text, re.S) if '图标题关键字' in s][0]
open('/tmp/diagram.svg','w',encoding='utf-8').write(svg)
EOF
python3 -c "import cairosvg; cairosvg.svg2png(url='/tmp/diagram.svg', write_to='/tmp/diagram.png', output_width=1500)"
# 然后用视觉模型按 layout-spec §7 检查单逐项复核
```
