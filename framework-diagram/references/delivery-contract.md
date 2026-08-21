# 离线 HTML/SVG 交付契约

生成或审查 HTML 时使用本契约；只编辑 Markdown/SVG 时不要擅自生成 HTML。

## 1. 输出门禁与权威源

- 只有用户明确要求“生成 HTML”“同步 MD/HTML”“更新同名 HTML”或审查既有 HTML
  时才处理 HTML。
- Markdown 是唯一手工内容源；生成的 HTML 不得手改。
- 成对交付时使用相同 basename，Markdown 与 HTML 语义同步。
- 保留用户指定的语言、术语和版本信息。

## 2. 完全离线

- 禁止 CDN、外部 JavaScript、远程或相邻 CSS、网络字体以及运行时 Mermaid。
- 禁止“缺少 SVG 时回退 CDN”；缺图必须使生成失败。
- 内嵌 SVG；普通本地图片转成 `data:` 资源。XML namespace URL 只是声明，不算
  网络依赖。
- 普通可点击链接可以保留；任何加载型 URL 都必须拒绝，包括 `script src`、
  `link href`、非 `data:` 的 `img src`/SVG `image href`、CSS `@import`/远程 `url()`。

## 3. SVG 可访问性与 ID

每个 SVG 必须同时满足：

```html
<svg viewBox="..." role="img" aria-labelledby="flow-title flow-desc">
  <title id="flow-title">……</title>
  <desc id="flow-desc">……</desc>
</svg>
```

- `title` 给出简短图名；`desc` 概括阅读顺序、主要节点和连线语义。
- `title`、`desc`、marker、clipPath、mask、gradient 等所有 ID 都以图名为前缀。
- 页面内 ID 不得重复；`url(#id)` 和 `aria-labelledby` 必须引用存在的 ID。
- 使用系统字体回退；禁止 `dominant-baseline`，多行文字用显式 `tspan y/dy`。

## 4. 生成与失败策略

- `FLOWCHART` 标记数、源图块数、提供的 SVG 数和生成 HTML 中的目标 SVG 数必须
  一致；未知图名、缺少 SVG、重复图名都要返回非零退出码。
- 生成器先写临时输出并完成校验，通过后再替换目标，避免失败时留下半成品。
- 批量生成器要报告生成文件数、图数和失败原因；`WARN` 不得以退出码 0 结束。

## 5. 最终检查

至少完成：

1. Markdown/HTML 同名配对和语义抽查；
2. 站内链接、锚点和本地资源检查；
3. 外部加载依赖扫描；
4. SVG XML、可访问性、重复 ID 和引用完整性检查；
5. 图块数量核对；
6. CJK 文字溢出、正交线、穿框和越界检查；
7. CairoSVG 渲染 PNG 后的视觉检查；
8. HTML 的窄屏、宽表格和打印布局检查；
9. 分阶段复制时，对暂存文件和最终目标执行 checksum 对比。

检查失败时修改 Markdown、SVG 图源或生成器并重新生成；不要直接修补生成 HTML。
