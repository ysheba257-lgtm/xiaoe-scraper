# xiaoe-scraper

**小鹅通课程视频一键批量下载器 —— 附带完整的浏览器爬虫 Skill**
**-- 可直接将文件扔给ai（一键启动）！！**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

滚动加载、密码保护、超多个视频的课程页面？一行命令，全自动搞定。

---

## 目录

- [环境要求](#环境要求)
- [安装](#安装)
- [完整使用流程](#完整使用流程)
  - [第一步：启动带远程调试的 Chrome](#第一步启动带远程调试的-chrome)
  - [第二步：打开课程页面并登录](#第二步打开课程页面并登录)
  - [第三步：一键下载（推荐）](#第三步一键下载推荐)
  - [第四步：分步模式（可选）](#第四步分步模式可选)
- [命令行参数](#命令行参数)
- [工作原理](#工作原理)
  - [整体架构](#整体架构)
  - [核心流程](#核心流程)
- [踩坑经验](#踩坑经验)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [故障排除](#故障排除)
- [贡献](#贡献)
- [许可证](#许可证)

---

## 环境要求

| 工具 | 版本要求 | 检查命令 |
|------|----------|----------|
| Python | ≥ 3.10 | `python --version` |
| Chrome / Edge | 最新版 | |
| ffmpeg | ≥ 4.0 | `ffmpeg -version` |

**ffmpeg** 必须在系统的 `PATH` 中。可以从 [ffmpeg.org](https://ffmpeg.org/) 下载，或通过包管理器安装。

> Windows 用户推荐：`winget install ffmpeg`，一行搞定。

---

## 安装

```bash
# 1. 克隆项目
git clone https://github.com/ysheba257-lgtm/xiaoe-scraper.git
cd xiaoe-scraper

# 2. 安装依赖
pip install -e .
playwright install chromium
```

> 不需要安装任何浏览器扩展。工具通过 CDP 协议（Chrome DevTools Protocol）直接和你手动启动的 Chrome 通信。

---

## 完整使用流程

### 第一步：启动带远程调试的 Chrome

Chrome 默认不会对外开放调试接口，需要手动开启。

**Windows** — 按 `Win + R`，输入：
```
chrome.exe --remote-debugging-port=9222
```

**macOS** — 打开终端：
```bash
open -a "Google Chrome" --args --remote-debugging-port=9222
```

**Linux**：
```bash
google-chrome --remote-debugging-port=9222
```

> Chrome 136 以上版本对默认用户目录会忽略 `--remote-debugging-port`。如果上述命令无效，加上 `--user-data-dir` 参数：
> ```
> chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chrome-debug-profile
> ```

### 第二步：打开课程页面并登录

在新启动的 Chrome 窗口中：
1. 打开课程链接（例如 `https://u3oz5.xetslk.com/s/xQK7I`）
2. 如果需要登录，完成登录
3. 确认页面已显示课程目录

### 第三步：一键下载（推荐）

```bash
python -m xiaoe_scraper all "https://u3oz5.xetslk.com/s/xQK7I" \
    --password 1341 \
    --out ./videos/
```

工具会自动完成以下操作：
- 连接到 Chrome
- 自动输入课程密码
- 滚动加载全部课程（包括虚拟滚动加载的隐藏条目）
- 提取每个视频的标题和资源 ID
- 逐个打开视频页，捕获 m3u8 链接，立即用 ffmpeg 下载

下载完成后，所有 `.mp4` 文件按 `序号_课程标题.mp4` 的命名保存到输出目录。

**实战示例**：

```bash
# 下载到 D 盘的"卓越增长视频"文件夹
python -m xiaoe_scraper all "https://u3oz5.xetslk.com/s/xQK7I" \
    --password 1341 \
    --out "D:/卓越增长视频/"

# 如果课程没有密码保护
python -m xiaoe_scraper all "https://example.xetslk.com/s/xxxxx" \
    --out ./videos/
```

### 第四步：分步模式（可选）

如果你希望先查看课程列表再决定下载哪些，可以分两步操作：

**步骤 A — 提取课程元数据**：

```bash
python -m xiaoe_scraper extract "https://u3oz5.xetslk.com/s/xQK7I" \
    --password 1341 \
    -o items.json
```

生成的 `items.json` 包含所有课程的 id 和标题：

```json
[
  {"id": "v_6a0abcb3e4b0694c5bc519ac", "name": "1.视频剪辑流程"},
  {"id": "v_6a0abcb5e4b0694c5bc519af", "name": "2.口播视频摄影师角度"},
  ...
]
```

**步骤 B — 下载视频**：

```bash
python -m xiaoe_scraper download items.json -o ./videos/
```

你可以在步骤 B 之前编辑 `items.json`，删除不需要的视频条目。

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--password`, `-p` | `""` | 课程解锁密码 |
| `--out`, `-o` | `./videos` | 视频输出目录 |
| `--cdp` | `http://localhost:9222` | Chrome 远程调试地址 |

三个子命令：

| 命令 | 用途 |
|------|------|
| `all` | 提取 + 下载，一步完成 |
| `extract` | 只提取课程列表，输出到 JSON |
| `download` | 从 JSON 文件批量下载 |

---

## 工作原理

### 整体架构

```
┌──────────────┐    CDP 协议    ┌───────────────┐    ffmpeg    ┌────────────┐
│   Chrome     │◄──────────────►│ xiaoe-scraper  │────────────►│  .mp4 文件 │
│ (9222 端口)  │                │  (Playwright)  │             │ (本地磁盘) │
└──────────────┘                └───────────────┘             └────────────┘
```

### 核心流程

1. **连接 Chrome** — 通过 CDP 连接到已打开的 Chrome，复用你的登录态
2. **自动解锁** — 检测页面是否需要密码，自动填写并提交
3. **虚拟滚动加载** — 小鹅通页面一次只渲染约 8 条课程，工具反复滚到底部，触发 API 分页加载，直到全部 68 条出现
4. **提取数据** — 从 Vue 2 组件树中直接读取 `SingleItemList`，获取资源 ID 和标题
5. **边采边下** — 逐个打开视频页，拦截 `.m3u8` 网络请求，立刻用 ffmpeg 下载（m3u8 签名约 10 分钟过期）

---

## 踩坑经验

以下是开发过程中遇到的 6 个关键问题和解决方案：

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | **只抓到 8 个视频** | 小鹅通使用虚拟滚动，DOM 只渲染可见条目 | 反复调用 `window.scrollTo(0, body.scrollHeight)`，等 DOM 稳定后再统计数量 |
| 2 | **找不到下载链接** | 课程列表是 Vue SPA，没有 `<a href>` 标签 | 直接读 Vue 组件树：`el.__vue__.$store.SingleItemList`，用 `resource_id` 构造视频 URL |
| 3 | **中文标题乱码** | Playwright 的 JS 求值通道会损坏 Unicode surrogate | 浏览器端用 `btoa(encodeURIComponent(text))` 转 base64，Python 端再解码 |
| 4 | **m3u8 链接过期** | CDN 签名 URL 有效期仅约 10 分钟 | 每获取一个 m3u8 立刻 ffmpeg 下载，不等其他视频 |
| 5 | **点击后元素失效** | SPA 导航导致 Playwright 的 ElementHandle 变 stale | 不用 ElementHandle 反复点击；先提取全部 ID，再逐个 `page.goto(video_url)` |
| 6 | **ffmpeg 报 httpproxy 错误** | Windows 代理环境下 ffmpeg 无法连接 | 在 ffmpeg 命令中显式添加 `httpproxy` 到协议白名单 |

---

## 项目结构

```
xiaoe-scraper/
├── xiaoe_scraper/
│   ├── __init__.py          # 包元数据
│   ├── __main__.py          # python -m 入口
│   ├── cli.py               # 命令行界面
│   ├── extractor.py         # 课程元数据提取（CDP→解锁→滚动→数据提取）
│   └── downloader.py        # m3u8 捕获 + ffmpeg 下载
├── README.md                # 项目文档
├── LICENSE                  # MIT 许可证
├── requirements.txt         # 依赖列表
├── pyproject.toml           # 安装配置
└── .gitignore
```

---

## 常见问题

**Q: 必须登录吗？**

是的。在启动远程调试的 Chrome 中打开课程页面并登录，工具会复用你的登录态。

**Q: 支持哪些平台？**

所有小鹅通（xiaoe-tech）搭建的课程平台。URL 中通常包含 `h5.xet.pomoho.com`、`xetslk.com` 或 `xiaoeknow.com`。

**Q: 能下载其他内容吗（PDF、音频）？**

目前仅支持视频。提取器会抓取所有条目，你可以修改下载器来支持其他类型。

**Q: 为什么不直接调 API？**

小鹅通的 API 需要客户端生成的签名参数。通过真实浏览器操作更稳定，也不容易被反爬。

**Q: m3u8 链接多久过期？**

约 10 分钟。所以工具采用"边采边下"策略，不会先存链接再下载。

**Q: 支持断点续传吗？**

目前不支持。如果下载中断，重新运行命令，已下载的文件会自动跳过。

---

## 故障排除

| 现象 | 解决方法 |
|------|----------|
| `Connection refused` 连接被拒绝 | Chrome 没有以远程调试模式运行。重新按第一步启动 Chrome |
| 只下载到 8 个视频 | 目录没有完全加载。确认"目录"标签页已激活，在页面手动滚动到底部再试 |
| `ffmpeg: command not found` | 安装 ffmpeg 并确保在 PATH 中 |
| 下载后无法播放 | 大概率是 m3u8 签名过期。大文件 (~1GB) 下载时间较长，重新运行重试该视频 |
| 中文终端乱码 | Windows 终端编码问题。运行前执行 `chcp 65001`，文件系统中的文件名不受影响 |

---

## 贡献

欢迎贡献！以下方向尤其需要帮助：

- **站点适配** — 针对不同小鹅通站点的特定配置
- **断点续传** — 中断后可从断点继续下载
- **更多内容类型** — PDF、音频、直播回放下载

提交 PR 前请先开 issue 讨论。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
