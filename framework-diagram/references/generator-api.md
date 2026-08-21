# 生成器 API 与范例

## 目录

1. 现成生成器位置
2. 范例图索引
3. Diagram API
4. 色块语义与两级图例 API
5. Markdown 侧标记
6. 布局节奏参考
7. 运行与验证

## 现成生成器位置

| 项目 | 生成器 | 说明 |
|------|--------|------|
| camera（A16） | `ZCode_docs/camera-porting/docs/tools/gen_html.py` | 首选参考：含泳带、自动图例、HTML 文末色块说明和失败型自检 |
| audio（A16） | `ZCode_docs/audio-porting/docs/tools/gen_audio_html.py` | audio 离线 SVG/HTML 生成器；改图时同步接入本规范的配色语义与两级图例 |

这些是来源项目路径，不保证在其他机器存在。新图优先在项目生成器中新增 FLOWS
定义；复用 API，不要照抄已知不合规的回退逻辑。

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
flow_id = "arch-overview"  # 同时作为所有 SVG id 的前缀
d = Diagram("图的可访问标题")

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

# 自由注释文字；颜色/连线图例由生成器从 class 自动生成
d.text(1164, 32, "本图的业务注释", cls="hint", anchor="end", size=11)

d.finish(1180, 755)   # 画布尺寸
```

注册：`FLOWS[flow_id] = _build_arch_overview()`。SVG 渲染器必须用 `flow_id` 生成
唯一 ID，例如 `arch-overview-title`、`arch-overview-desc`、
`arch-overview-arr-data`，并输出：

```html
<svg viewBox="0 0 1180 755" role="img"
     aria-labelledby="arch-overview-title arch-overview-desc">
  <title id="arch-overview-title">图的可访问标题</title>
  <desc id="arch-overview-desc">从应用层到硬件层的数据与控制路径。</desc>
</svg>
```

## 色块语义与两级图例 API

以 camera 生成器的 `NODE_LEGEND` 为规范实现：一份数据同时驱动图内图例、
SVG `<desc>` 和 HTML 文末说明；节点 CSS 从该数据生成或由自检逐项核对。

```python
NODE_LEGEND = (
    # class, label, fill, stroke, dash
    ("hal", "HAL/用户态框架", "#dcfce7", "#16a34a", ""),
    ("hw", "SoC 硬件", "#fae8ff", "#a21caf", ""),
    ("note", "可选/说明", "#fff7ed", "#ea580c", "5 3"),
    # 完整列表见 layout-spec §3
)

# 每张图：根据 d.nodes / d.edges 的实际 class 生成紧凑图例
legend, legend_height, legend_desc = legend_svg(d, marker_ids)

# 每篇 HTML：在 </article> 前插入完整配色说明
TEMPLATE = """...{body}{color_guide}</article>..."""
color_guide = color_guide_html()
```

完成条件：

- 每张 SVG 恰有一个 `g.legend`，其节点/边 class 集合与实际集合相等；
- 每篇 HTML 恰有一个 `section.color-key`，位于 `</article>` 前并包含完整节点类别；
- 页面说明使用两列网格，`@media(max-width:700px)` 切换为单列；
- 颜色含义固定为职责/层级，不用于表达顺序、成败或数据格式。

## Markdown 侧标记

~~~~markdown
<!-- FLOWCHART: arch-overview -->
```text
（原 ASCII 图保留在此，生成器替换为 SVG 并把 ASCII 收进 <details>）
```
~~~~

也可使用 `mermaid` 代码块。规则：标记名 = FLOWS 键名；标记必须紧跟代码块
（中间只允许空行）。标记缺失、未知名称或缺少 SVG 时必须失败，禁止 CDN 回退。

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

生成 HTML 后继续执行 `delivery-contract.md` 的最终检查。至少核对同名 MD/HTML、
FLOWCHART 与 SVG 数量、站内链接、外部加载依赖、重复 ID，以及暂存/目标 checksum。
