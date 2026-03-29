# 贡献指南 | Contributing Guide

感谢你愿意为 **Vibe-Lawyering** 做出贡献！本项目的成长离不开每一位法律人和技术人的参与。

Thank you for your interest in contributing to **Vibe-Lawyering**! This project grows with every lawyer and technologist who participates.

---

## 目录 | Contents

- [行为准则](#行为准则)
- [贡献类型](#贡献类型)
- [提交流程](#提交流程)
- [内容规范](#内容规范)
- [本地开发](#本地开发)

---

## 行为准则

参与本项目即表示你同意遵守以下准则：

- **专业尊重**：以尊重和专业的态度对待所有参与者
- **建设性反馈**：批评时聚焦内容本身，而非个人
- **知识共享**：鼓励分享，反对抄袭和未授权转载
- **法律边界**：所有内容须符合相关法律法规，不得包含违法信息

## Code of Conduct

By participating in this project, you agree to:

- **Respect**: Treat all participants with respect and professionalism
- **Constructive feedback**: Focus criticism on content, not individuals
- **Knowledge sharing**: Encourage sharing; oppose plagiarism
- **Legal compliance**: All content must comply with applicable laws

---

## 贡献类型

### ⚡ 贡献 Agent Skills

欢迎提交你在法律工作中验证有效的 AI Agent 提示词或技能配置。

**要求：**
- 提供清晰的使用场景说明
- 包含示例输入和输出
- 说明适用的 AI 平台（Claude / GPT / 通义 等）
- 标注测试过的效果和局限性

**文件位置：** `agent-skills/` 目录下，按场景分类

---

### 🗄️ 贡献 MCP 资源

欢迎提交法律数据库的 MCP 接入配置、工具说明或使用教程。

**要求：**
- 提供数据库基本信息（名称、覆盖范围、收费情况）
- 提供 MCP 配置代码（如可公开）
- 包含接入步骤说明
- 注明数据库的授权使用要求

**文件位置：** `mcp-servers/` 目录下

---

### 🎓 贡献课程资源

欢迎提交面向法律人的 AI 使用教程、编程课程资源或学习路径。

**要求：**
- 明确目标受众（无基础 / 初级 / 中级）
- 提供课程链接或内容摘要
- 注明课程语言、时长和费用（免费/付费）
- 优先推荐免费、开放的资源

**文件位置：** `courses/` 目录下

---

### 🐛 报告问题

如果你发现内容有误、链接失效或有改进建议，请[提交 Issue](https://github.com/zhouziyue233/Vibe-Lawyering/issues)。

---

## 提交流程

### 第一步：Fork 本项目

点击页面右上角的 **Fork** 按钮，将项目复制到你的账号下。

```bash
git clone https://github.com/YOUR_USERNAME/Vibe-Lawyering.git
cd Vibe-Lawyering
```

### 第二步：创建分支

```bash
git checkout -b feature/your-contribution-name
# 示例：git checkout -b feature/add-contract-review-skill
```

### 第三步：进行修改

遵照本文档中的内容规范进行修改或新增内容。

### 第四步：提交变更

```bash
git add .
git commit -m "feat: add [描述你的贡献]"
git push origin feature/your-contribution-name
```

**Commit 消息规范：**

| 前缀 | 用途 |
|------|------|
| `feat:` | 新增内容或功能 |
| `fix:` | 修复错误或失效链接 |
| `docs:` | 文档改进 |
| `refactor:` | 结构调整，不涉及内容变更 |

### 第五步：提交 Pull Request

前往 GitHub 页面，点击 **New Pull Request**，填写 PR 模板中的信息。

---

## 内容规范

### Markdown 格式

- 每个文件顶部包含简短的中英双语描述
- 使用标准的 Markdown 标题层级（H1 → H2 → H3）
- 表格对齐，方便阅读
- 中文内容与英文字母/数字之间加空格（例如："使用 Claude 处理合同"）

### 资源链接

- 确认链接在提交时有效
- 对于付费资源，请在旁边标注 `[付费]`
- 对于中文资源，请标注 `[中文]`
- 对于英文资源，请标注 `[EN]`

### 技能提示词

- 提示词应使用清晰的分隔符（如 `---` 或 XML 标签）结构化内容
- 包含"角色定义"、"任务说明"、"输出格式"三个基本部分
- 避免包含任何真实案例的隐私信息

---

## 本地开发

本项目为纯 Markdown 文档项目，无需特殊环境。你只需要：

1. 一个文本编辑器（推荐 VS Code + Markdown Preview 插件）
2. Git

如需在本地预览 Markdown：

```bash
# 安装 markserv（可选）
npm install -g markserv
markserv .
```

---

## 联系我们

有任何问题欢迎通过以下方式联系：

- 📋 [GitHub Issues](https://github.com/zhouziyue233/Vibe-Lawyering/issues)
- 💬 [GitHub Discussions](https://github.com/zhouziyue233/Vibe-Lawyering/discussions)

**再次感谢你的贡献！每一份分享都在推动法律行业的 AI 普及。**

*Thank you again for contributing! Every share helps advance AI adoption in the legal industry.*
