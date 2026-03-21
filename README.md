<div align="center">

# ⚖️ Vibe-Lawyering

**法律人的 AI 工具箱**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/zhouziyue233/Vibe-Lawyering?style=social)](https://github.com/zhouziyue233/Vibe-Lawyering)
[![Contributors](https://img.shields.io/github/contributors/zhouziyue233/Vibe-Lawyering)](https://github.com/zhouziyue233/Vibe-Lawyering/graphs/contributors)

> 聚合法律人所需的 Agent Skills、法律数据库 MCP 工具与 AI/编程教育资源的开源社区项目

[**English**](README_EN.md) · [快速开始](#-快速开始) · [贡献指南](CONTRIBUTING.md)

</div>

---

## 📖 目录

- [项目简介](#-项目简介)
- [模块概览](#-模块概览)
- [快速开始](#-快速开始)
- [Agent Skills](#-agent-skills)
- [MCP 资源库](#-mcp-资源库)
- [AI & 编程课程](#-ai--编程课程)
- [如何贡献](#-如何贡献)
- [社区](#-社区)
- [许可证](#-许可证)

---

## 🇨🇳 项目简介

**Vibe-Lawyering** 是一个面向法律人（律师、法学研究者、法务、法官、检察官等）的开源资源聚合平台，旨在降低法律行业拥抱 AI 工具的门槛。

| 模块 | 内容 |
|------|------|
| ⚡ **Agent Skills** | 精选的法律领域 AI Agent 技能配置，可直接接入 Claude、GPT 等 |
| 🗄️ **MCP 资源库** | 法律数据库 MCP 工具列表与接入指南（北大法宝、威科先行、法信等） |
| 🎓 **AI & 编程课程** | 面向法律人的零基础 AI 使用与编程入门课程资源 |

---

## 🗂️ 模块概览

```
Vibe-Lawyering/
├── 📁 agent-skills/        # 法律 AI Agent 技能库
│   ├── contract-review     # 合同审查
│   ├── legal-research      # 法律检索与研究
│   ├── compliance-check    # 合规审查
│   ├── nda-triage          # NDA 快速筛查
│   └── litigation-support  # 诉讼辅助
├── 📁 mcp-resources/       # 法律数据库 MCP 工具
│   ├── chinese-legal-dbs   # 中国法律数据库
│   ├── international-dbs   # 国际法律数据库
│   └── setup-guides        # 配置接入指南
├── 📁 courses/             # AI & 编程课程资源
│   ├── ai-for-lawyers      # 法律人 AI 应用
│   └── coding-for-lawyers  # 法律人编程入门
├── 📄 CONTRIBUTING.md      # 贡献指南
└── 📄 LICENSE              # MIT 许可证
```

---

## 🚀 快速开始

### 使用 Agent Skills

1. 浏览 [`agent-skills/`](agent-skills/README.md) 目录，找到你需要的技能
2. 按照技能页面的说明，复制 Prompt 或安装配置文件
3. 在你使用的 AI 工具（Claude、GPT、Coze 等）中加载该技能

### 接入法律数据库 MCP

1. 浏览 [`mcp-resources/`](mcp-resources/README.md) 了解支持的数据库列表
2. 按照 [`setup-guides/`](mcp-resources/setup-guides/) 中的教程完成接入
3. 结合 Agent Skills 实现"检索 + 分析"一体化工作流

### 学习 AI & 编程

1. 进入 [`courses/`](courses/README.md) 按照学习路径选择课程
2. 无需编程基础，法律场景贯穿全程

---

## ⚡ Agent Skills

法律专属 AI 技能，覆盖核心法律工作场景：

| 技能 | 描述 | 难度 |
|------|------|------|
| [合同审查](agent-skills/README.md#合同审查) | 自动标注风险条款，生成修改建议 | ⭐⭐ |
| [法律研究](agent-skills/README.md#法律研究助手) | 案例检索、法规梳理、综述生成 | ⭐⭐ |
| [合规审查](agent-skills/README.md#合规风险评估) | 商业行为合规风险评估 | ⭐⭐⭐ |
| [NDA 快速筛查](agent-skills/README.md#nda-快速筛查) | 保密协议关键条款一键识别 | ⭐ |
| [诉讼辅助](agent-skills/README.md#诉讼文书起草) | 裁判文书分析、起诉状草拟 | ⭐⭐⭐ |

👉 [查看全部 Agent Skills →](agent-skills/README.md)

---

## 🗄️ MCP 资源库

支持主流法律数据库的 Model Context Protocol 工具：

### 中国法律数据库

| 数据库 | MCP 状态 | 说明 |
|--------|----------|------|
| 北大法宝 | 🟡 开发中 | 法规、案例、期刊全覆盖 |
| 威科先行 | 🟡 开发中 | 法律法规、司法案例 |
| 法信 | 🟡 开发中 | 最高人民法院官方平台 |
| 中国裁判文书网 | ✅ 可用 | 裁判文书公开数据 |
| 国家法律法规数据库 | ✅ 可用 | 全国人大官方法规库 |

### 国际法律数据库

| 数据库 | MCP 状态 | 说明 |
|--------|----------|------|
| Westlaw | 🔴 计划中 | 美国法律数据库 |
| LexisNexis | 🔴 计划中 | 国际法律信息平台 |
| HeinOnline | 🟡 开发中 | 法律期刊数据库 |
| EUR-Lex | ✅ 可用 | 欧盟法律数据库 |

👉 [查看全部 MCP 资源 →](mcp-resources/README.md)

---

## 🎓 AI & 编程课程

为法律人量身定制的学习资源，无需技术背景：

### 🤖 AI 应用课程

| 课程名称 | 描述 | 链接 |
|----------|------|------|
| AI 工具入门：法律人的提示词技巧 | 零基础入门，六大核心提示词技巧，含法律场景专项练习 | [查看课程](courses/ai-for-lawyers.md#提示词技巧) |
| 用 Claude 辅助合同审查 | 合同审查 AI 工作流设计，风险条款识别与修改建议生成 | [查看课程](courses/ai-for-lawyers.md#合同审查实战) |
| AI 辅助法律研究工作流 | 文献检索、案例分析自动化，可搭配 MCP 数据库工具使用 | [查看课程](courses/ai-for-lawyers.md#研究工作流) |
| 法律 AI 产品评测与选型 | 主流法律 AI 产品横向对比，选型框架与团队推广方法论 | [查看课程](courses/ai-for-lawyers.md#产品选型) |
| Claude Code 系列教程（法律人版） | Anthropic 命令行 AI 编程工具教程合集，帮助法律人快速搭建自动化工具，无需深厚编程背景 | [查看教程 →](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkzMjg2NTcxNA==&scene=1&album_id=4406622888632549382&count=3#wechat_redirect) |

### 💻 编程入门课程

| 课程名称 | 描述 | 链接 |
|----------|------|------|
| Python 零基础：处理法律文本数据 | Python 基础语法，读取 Word/PDF，批量整理案件数据 | [查看课程](courses/coding-for-lawyers.md#python入门) |
| 用代码批量处理合同 | 批量读取合同文件夹，提取关键信息，生成合同台账 Excel | [查看课程](courses/coding-for-lawyers.md#批量处理合同) |
| 数据可视化：让法律数据讲故事 | 案件数据统计分析，胜诉率图表，裁判文书地区热力图 | [查看课程](courses/coding-for-lawyers.md#数据可视化) |
| 构建你的第一个法律 AI 工具 | 调用 Claude API 处理法律文本，构建合同批量审查工具并部署 | [查看课程](courses/coding-for-lawyers.md#构建法律工具) |

---

## 🤝 如何贡献

我们欢迎一切形式的贡献！

- 🐛 **提交 Issue**：发现错误或有新想法，[点此提交](https://github.com/zhouziyue233/Vibe-Lawyering/issues)
- 📝 **提交 PR**：添加新 Skill、MCP 工具或课程资源
- 🌟 **给项目点星**：帮助更多法律人发现这个项目
- 📣 **传播分享**：推荐给你的同事和法律人社群

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 💬 社区

- 💬 [GitHub Discussions](https://github.com/zhouziyue233/Vibe-Lawyering/discussions) — 提问、分享、交流
- 🐦 [Twitter / X](https://twitter.com/VibeLaywering) — 最新动态
- 📮 有合作意向？请发邮件至 `contact@vibe-lawyering.dev`

---

## ⭐ 贡献者

感谢所有为本项目做出贡献的人！

<!-- ALL-CONTRIBUTORS-LIST:START -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**用 AI 赋能法律人**

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

</div>
