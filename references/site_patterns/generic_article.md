# Generic Article Site Pattern

## 普通文章页抽取逻辑

- 优先识别 `meta[property="og:title"]`、`meta[name="twitter:title"]` 和 HTML `<title>`。
- 正文区域优先使用 `<article>`，其次尝试 `<main>`，再回退到 `<body>`。
- 如页面包含 JSON-LD，可作为后续增强方向读取 `headline`、`datePublished`、`author` 等字段。
- 静态 HTML 失败时可尝试 Jina Reader 生成 markdown，再回退到 static text。

## 失败兜底

- HTTP 错误、空正文、动态渲染不足或权限提示都应记录为 failed、partial 或 manual_required。
- 单篇失败不得中断 pipeline。
- 对付费、登录、验证码或访问限制页面，只记录失败原因，不尝试绕过限制。
