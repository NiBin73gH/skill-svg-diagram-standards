#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""framework-diagram skill 的最小可运行参考实现。

提供 references/ 中描述的核心构件：

- ``NODE_LEGEND``：配色语义源（layout-spec.md §3），同时驱动图内图例、
  SVG ``<desc>`` 与 HTML 文末色块说明；
- ``Diagram``：band / box / 锚点 / edge / text / finish API
  （generator-api.md §3），节点高度自动 = 行数×18+16，图例在 finish()
  时从实际使用的 class 集合自动生成并整体下移正文；
- ``color_guide_html()``：HTML 文末完整色块说明（delivery-contract.md §5）；
- 单图自检：XML 可解析、可访问性引用、重复 ID、无 dominant-baseline、
  文字估宽溢出、非正交线段、连线穿框、画布越界、图例与实际 class 一致。

刻意不覆盖的部分（属于完整生成器的职责，见 generator-api.md）：
批量 MD→HTML 重建、FLOWCHART 标记替换、每篇 HTML 恰一份 color-key、
站内链接与 checksum 检查。

用法::

    python3 examples/diagram_lib.py    # 生成 demo.svg + demo.html 并自检
"""

import html
import os
import sys
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------- 配色语义源
# (class, 语义名称, 填充, 边框, 虚线 dash；dash 为空串表示实线)
NODE_LEGEND = [
    ("app",      "应用层",          "#dbeafe", "#2563eb", ""),
    ("hal",      "HAL/用户态框架",  "#dcfce7", "#16a34a", ""),
    ("kernel",   "内核/驱动",       "#ffedd5", "#ea580c", ""),
    ("sensor",   "外设/器件",       "#e0e7ff", "#4f46e5", ""),
    ("hw",       "SoC/DSP 硬件",    "#fae8ff", "#a21caf", ""),
    ("api",      "接口/配置契约",   "#fef9c3", "#ca8a04", ""),
    ("node",     "中性逻辑/结果",   "#e0f2fe", "#0284c7", ""),
    ("sink",     "输出/终点",       "#f1f5f9", "#64748b", ""),
    ("build",    "构建/生成物",     "#e2e8f0", "#475569", ""),
    ("disabled", "已禁用",          "#fee2e2", "#dc2626", "5 3"),
    ("note",     "可选/说明",       "#fff7ed", "#ea580c", "5 3"),
]
LEGEND_MAP = {c: (lab, f, s, d) for c, lab, f, s, d in NODE_LEGEND}

# (cls, 含义, 颜色, 粗细, dasharray, 箭头) —— layout-spec.md §4
EDGE_STYLES = {
    "":     ("控制面/命令",    "#64748b", 1.8, "",     True),
    "data": ("数据面",         "#0284c7", 2.2, "",     True),
    "up":   ("带外/上行回读",  "#d97706", 1.8, "6 4",  True),
    "link": ("关联关系",       "#94a3b8", 1.4, "5 4",  False),
}

FONT = "system-ui, -apple-system, 'Segoe UI', 'Noto Sans CJK SC', sans-serif"
VPAD, HPAD, LINE_H = 8, 13, 18


def est_width(text, size):
    """CJK 感知估宽：CJK≈1em、ASCII≈0.6em、空格≈0.3em（layout-spec.md §3）。"""
    em = sum(0.3 if ch == " " else (1.0 if ord(ch) > 0x2E80 else 0.6) for ch in text)
    return em * size


def _esc(s):
    return html.escape(s, quote=True)


class Diagram:
    """单张离线 SVG 的构建器。所有 id 以 flow_id 为前缀。"""

    def __init__(self, flow_id, title, desc=""):
        self.fid = flow_id
        self.title = title
        self.desc = desc
        self.bands = []   # {x,y,w,h,title}
        self.nodes = {}   # nid -> {x,y,w,h,lines,cls}
        self.edges = []   # {pts,label,label_pos,cls,anchor}
        self.texts = []   # {x,y,s,cls,anchor,size}
        self._used_node_cls = set()
        self._used_edge_cls = set()

    # ------------------------------------------------------------- 元素定义
    def band(self, x, y, w, h, title):
        """泳道带；标题基线自动在 y+23，带内节点顶应摆在 y+48（硬性）。"""
        self.bands.append({"x": x, "y": y, "w": w, "h": h, "title": title})

    def box(self, nid, x, y, w, text, cls="node"):
        """节点；高度自动 = 行数×18+16，不要手算。行首基线 = y+VPAD+11。"""
        if nid in self.nodes:
            raise ValueError(f"重复节点 id: {nid}")
        lines = text.split("\n")
        for ln in lines:  # 估宽自检前置：溢出直接失败，不产出坏 SVG
            if est_width(ln, 12.5) + 2 * HPAD > w + 1e-6:
                raise ValueError(f"节点 {nid} 第 {lines.index(ln)+1} 行文字估宽溢出框宽")
        h = len(lines) * LINE_H + 2 * VPAD
        self.nodes[nid] = {"x": x, "y": y, "w": w, "h": h, "lines": lines, "cls": cls}
        self._used_node_cls.add(cls)
        return h

    # 锚点：端点必须用这些取，禁止手算坐标（generator-api.md §3）
    def top(self, nid, dx=0.0):
        n = self.nodes[nid]
        return (n["x"] + n["w"] / 2 + dx, n["y"])

    def bottom(self, nid, dx=0.0):
        n = self.nodes[nid]
        return (n["x"] + n["w"] / 2 + dx, n["y"] + n["h"])

    def left(self, nid):
        n = self.nodes[nid]
        return (n["x"], n["y"] + n["h"] / 2)

    def right(self, nid):
        n = self.nodes[nid]
        return (n["x"] + n["w"], n["y"] + n["h"] / 2)

    def edge(self, pts, label=None, label_pos=None, cls="", anchor="middle"):
        """正交折线点列。cls: "" 控制面 | "data" 数据面 | "up" 带外 | "link" 关联。"""
        self.edges.append({"pts": [tuple(p) for p in pts], "label": label,
                           "label_pos": label_pos, "cls": cls, "anchor": anchor})
        self._used_edge_cls.add(cls)

    def text(self, x, y, s, cls="hint", anchor="start", size=11):
        self.texts.append({"x": x, "y": y, "s": s, "cls": cls, "anchor": anchor, "size": size})

    # ------------------------------------------------------------- 渲染
    def _legend_groups(self, canvas_w):
        """按实际使用的 class 生成图例条目（自动换行），返回 (行列表, 总高)。"""
        rows, row = [], []
        items = [("node:" + c, LEGEND_MAP[c][0], c) for c in
                 sorted(self._used_node_cls, key=lambda c: [n[0] for n in NODE_LEGEND].index(c))]
        items += [("edge:" + c, EDGE_STYLES[c][0], c) for c in
                  sorted(self._used_edge_cls, key=lambda c: list(EDGE_STYLES).index(c))]
        for it in items:
            wpx = 16 + 6 + est_width(it[1], 11) + 22
            if row and 16 + sum(r[1] for r in row) + wpx > canvas_w - 32:
                rows.append(row)
                row = []
            row.append((it, wpx))
        if row:
            rows.append(row)
        return rows, 12 + 24 * len(rows) + 10

    def _apply_dy(self, dy):
        for b in self.bands:
            b["y"] += dy
        for n in self.nodes.values():
            n["y"] += dy
        for e in self.edges:
            e["pts"] = [(x, y + dy) for x, y in e["pts"]]
            if e["label_pos"]:
                e["label_pos"] = (e["label_pos"][0], e["label_pos"][1] + dy)
        for t in self.texts:
            t["y"] += dy

    def finish(self, w, h):
        """返回 (svg 字符串, 总高)。图例画在顶部，正文整体下移。"""
        rows, lh = self._legend_groups(w)
        self._apply_dy(lh + 12)
        fid, out = self.fid, []
        out.append(
            f'<svg viewBox="0 0 {w} {h + lh + 12}" role="img" '
            f'aria-labelledby="{fid}-title {fid}-desc" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">')
        out.append(f'<title id="{fid}-title">{_esc(self.title)}</title>')
        used = "、".join(LEGEND_MAP[c][0] for c in self._used_node_cls)
        out.append(f'<desc id="{fid}-desc">{_esc(self.desc or self.title)}。'
                   f'本图使用的节点颜色语义：{_esc(used)}。</desc>')
        out.append(f'<defs>')
        for cls, (_, color, _, dash, arrow) in EDGE_STYLES.items():
            if cls not in self._used_edge_cls or not arrow:
                continue
            out.append(f'<marker id="{fid}-arr-{cls or "ctrl"}" viewBox="0 0 10 10" '
                       f'refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                       f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')
        out.append('</defs>')
        out.append(f'<rect class="bg" x="0" y="0" width="{w}" height="{h + lh + 12}" fill="#fbfcfe"/>')

        # 图例（g.legend）：只列实际使用的 class（layout-spec.md §5.1）
        out.append(f'<g class="legend">')
        out.append(f'<rect x="16" y="12" width="{w - 32}" height="{lh}" rx="8" fill="#eef2f7"/>')
        out.append(f'<text x="28" y="{12 + 24}" font-size="11" fill="#475569" font-weight="bold">图例</text>')
        for ri, row in enumerate(rows):
            x = 70
            y = 12 + 24 * (ri + 1)
            for (kind, label, cls), _ in row:
                if kind.startswith("node:"):
                    _, fill, stroke, dash = LEGEND_MAP[cls]
                    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
                    out.append(f'<rect data-lg="{kind}" x="{x:.0f}" y="{y - 10}" width="16" height="12" '
                               f'rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{dash_attr}/>')
                    x += 22
                else:
                    _, color, lw, dash, _arrow = EDGE_STYLES[cls]
                    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
                    out.append(f'<line data-lg="{kind}" x1="{x:.0f}" y1="{y - 4}" x2="{x + 24:.0f}" y2="{y - 4}" '
                               f'stroke="{color}" stroke-width="{lw}"{dash_attr}/>')
                    x += 30
                out.append(f'<text x="{x:.0f}" y="{y}" font-size="11" fill="#334155">{_esc(label)}</text>')
                x += est_width(label, 11) + 22
        out.append('</g>')

        for b in self.bands:
            out.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" rx="12" '
                       f'fill="#f8fafc" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="6 4"/>')
            out.append(f'<text x="{b["x"] + 16}" y="{b["y"] + 23}" font-size="14" '
                       f'font-weight="bold" fill="#475569">{_esc(b["title"])}</text>')

        for nid, n in self.nodes.items():
            _, fill, stroke, dash = LEGEND_MAP[n["cls"]]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<g id="{fid}-{nid}"><rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" '
                       f'height="{n["h"]}" rx="8" fill="{fill}" stroke="{stroke}" '
                       f'stroke-width="1.5"{dash_attr}/>')
            for i, ln in enumerate(n["lines"]):
                by = n["y"] + VPAD + 11 + i * LINE_H
                out.append(f'<text x="{n["x"] + n["w"] / 2:.1f}" y="{by}" font-size="12.5" '
                           f'fill="#1e293b" text-anchor="middle">{_esc(ln)}</text>')
            out.append('</g>')

        for e in self.edges:
            _, color, lw, dash, arrow = EDGE_STYLES[e["cls"]]
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in e["pts"])
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            marker = f' marker-end="url(#{fid}-arr-{e["cls"] or "ctrl"})"' if arrow else ""
            out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                       f'stroke-width="{lw}"{dash_attr}{marker}/>')
            if e["label"] and e["label_pos"]:
                out.append(f'<text x="{e["label_pos"][0]}" y="{e["label_pos"][1]}" font-size="11" '
                           f'font-weight="bold" fill="#334155" text-anchor="{e["anchor"]}">'
                           f'{_esc(e["label"])}</text>')

        for t in self.texts:
            cls_color = "#94a3b8" if t["cls"] == "hint" else "#334155"
            out.append(f'<text x="{t["x"]}" y="{t["y"]}" font-size="{t["size"]}" '
                       f'fill="{cls_color}" text-anchor="{t["anchor"]}">{_esc(t["s"])}</text>')
        out.append('</svg>')
        return "\n".join(out), h + lh + 12

    # ------------------------------------------------------------- 自检
    def self_check(self, svg, total_h, canvas_w):
        """单图自检（layout-spec.md §6 的可自动化子集）。返回错误列表。"""
        errs = []
        try:
            # 输入是 finish() 刚生成的字符串（可信）；若把自检接到处理
            # 外部 HTML 的完整生成器里，请换用 defusedxml.ElementTree。
            root = ET.fromstring(svg)
        except ET.ParseError as ex:
            return [f"SVG 不是合法 XML: {ex}"]

        ids = [el.get("id") for el in root.iter() if el.get("id")]
        if len(ids) != len(set(ids)):
            errs.append("存在重复 id")
        labelled = root.get("aria-labelledby", "").split()
        idset = set(ids)
        for ref in labelled:
            if ref not in idset:
                errs.append(f"aria-labelledby 引用不存在的 id: {ref}")
        for tag in ("{http://www.w3.org/2000/svg}title", "{http://www.w3.org/2000/svg}desc"):
            if root.find(tag) is None:
                errs.append(f"缺少 <{tag.split('}')[1]}>")
        if "dominant-baseline" in svg:
            errs.append("使用了 dominant-baseline（cairosvg 不支持）")

        for nid, n in self.nodes.items():  # 越界（含文字框）
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > canvas_w or n["y"] + n["h"] > total_h:
                errs.append(f"节点 {nid} 越出画布")

        for e in self.edges:
            pts = e["pts"]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):  # 正交
                if abs(round(x1) - round(x2)) > 0 and abs(round(y1) - round(y2)) > 0:
                    errs.append(f"边 {pts} 存在斜线段")
            for x, y in pts:  # 越界
                if not (0 <= x <= canvas_w and 0 <= y <= total_h):
                    errs.append(f"边 {pts} 越出画布")
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):  # 穿框（正交段 vs 收缩 2px 的框内部）
                for nid, n in self.nodes.items():
                    ix0, iy0 = n["x"] + 2, n["y"] + 2
                    ix1, iy1 = n["x"] + n["w"] - 2, n["y"] + n["h"] - 2
                    if abs(y1 - y2) < 1e-6:  # 水平段
                        if iy0 < y1 < iy1 and min(x1, x2) < ix1 and max(x1, x2) > ix0:
                            errs.append(f"边穿过节点 {nid}（水平段 y={y1:.0f}）")
                    else:  # 竖直段
                        if ix0 < x1 < ix1 and min(y1, y2) < iy1 and max(y1, y2) > iy0:
                            errs.append(f"边穿过节点 {nid}（竖直段 x={x1:.0f}）")

        legend_kinds = {el.get("data-lg") for el in root.iter() if el.get("data-lg")}
        expect = {f"node:{c}" for c in self._used_node_cls} | {f"edge:{c}" for c in self._used_edge_cls}
        if legend_kinds != expect:
            errs.append(f"图例与实际 class 不一致: 图例 {sorted(legend_kinds)} vs 实际 {sorted(expect)}")
        return errs


def color_guide_html():
    """HTML 文末完整色块说明（delivery-contract.md §5；每篇恰一份，</article> 前）。"""
    items = []
    for cls, label, fill, stroke, dash in NODE_LEGEND:
        style = f"background:{fill};border-color:{stroke}"
        if dash:
            style += ";border-style:dashed"
        items.append(f'<li><span class="sw" style="{style}"></span><b>{_esc(label)}</b>'
                     f'<span class="why"> — {_esc(_NODE_WHY[cls])}</span></li>')
    return ('<section class="color-key" aria-labelledby="flow-color-key-title">'
            '<h2 id="flow-color-key-title">流程图色块说明</h2>'
            '<p>色块仅用于区分模块的职责或技术层级，不表示执行顺序、成功/失败或数据格式。</p>'
            f'<ul>{"".join(items)}</ul></section>')


_NODE_WHY = {
    "app": "App 与直接面向用户的功能", "hal": "CamX、CHI、PAL 等处理逻辑",
    "kernel": "驱动与内核侧实现", "sensor": "外部解码器、Sensor 等器件",
    "hw": "CSIPHY、CSID、I2S 等硬件资源", "api": "属性、XML、API、元数据及约束",
    "node": "不归属特定硬件层的节点或结果", "sink": "预览、录像、Surface 等最终输出",
    "build": "构建配置、打包过程及生成文件", "disabled": "关闭、禁用或绕过的模块",
    "note": "可选路径、补充说明或注意事项",
}

_DEMO_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>framework-diagram demo</title>
<style>
 body{{margin:0;background:#f8fafc;font-family:{font};color:#1e293b}}
 article{{max-width:1240px;margin:0 auto;padding:24px;background:#fff}}
 svg{{max-width:100%;height:auto}}
 .color-key ul{{list-style:none;padding:0;margin:16px 0 0;display:grid;
   grid-template-columns:repeat(2,1fr);gap:10px 24px}}
 .color-key li{{display:flex;align-items:center;gap:8px}}
 .sw{{display:inline-block;width:16px;height:12px;border-radius:3px;
   border:1.5px solid;flex:none}}
 @media(max-width:700px){{.color-key ul{{grid-template-columns:1fr}}}}
</style></head><body><article>
<h1>framework-diagram 最小参考实现 demo</h1>
<p>本页由 examples/diagram_lib.py 生成：SVG 完全离线、可访问（title/desc/
aria-labelledby），图例从实际使用的 class 自动推导，文末带完整色块说明。</p>
{svg}{color_guide}</article></body></html>"""


def _demo():
    d = Diagram("audio-flow-demo", "示例：三层泳道总览",
                "自上而下为应用层、HAL 用户态与内核驱动；灰实线为控制面，蓝粗线为数据面")
    # 泳带 y=12/132/282，带间 20px；节点顶一律 band_y+48（标题基线 band_y+23 下净空 25px）
    d.band(16, 12, 1148, 100, "Application (AOSP)")
    d.band(16, 132, 1148, 130, "Vendor HAL (userspace)")
    d.band(16, 282, 1148, 110, "Kernel Drivers")
    d.box("app1", 52, 60, 300, "AudioTrack / AudioRecord\nAudioFlinger · AudioPolicyService", "app")
    d.box("hal1", 52, 180, 300, "PAL → AGM", "hal")
    d.box("hal2", 432, 180, 300, "libar-gsl (Graph Service Layer)", "hal")
    d.box("kern1", 52, 330, 300, "audio-kernel\ngpr-lite / audio-pkt", "kernel")
    d.edge([d.bottom("app1"), d.top("hal1")], "open / start", (212, 126), "", "start")
    d.edge([d.right("hal1"), d.left("hal2")], cls="link")
    # 数据面绕行边：拐点 x 与进入锚点 x 对齐（262→262、342→342），全正交；
    # 水平段走在带 2/带 3 间隙中点 y=272，标签距边界线与连线均 ≥3px
    d.edge([d.bottom("hal1", 60), (262, 272), (342, 272), d.top("kern1", 140)],
           "graph 拓扑下发", (302, 266), cls="data")
    svg, th = d.finish(1180, 412)
    errs = d.self_check(svg, th, 1180)
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "demo.svg"), "w", encoding="utf-8").write(svg)
    open(os.path.join(here, "demo.html"), "w", encoding="utf-8").write(
        _DEMO_HTML.format(font=FONT, svg=svg, color_guide=color_guide_html()))
    print(f"demo.svg / demo.html 已生成（viewBox 1180x{th}），自检 "
          f"{'通过' if not errs else '失败'}")
    for e in errs:
        print("  ERROR:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(_demo())
