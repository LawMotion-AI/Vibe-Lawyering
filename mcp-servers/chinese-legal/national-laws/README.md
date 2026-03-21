# 国家法律法规数据库 MCP Server

对接[国家法律法规数据库](https://flk.npc.gov.cn/)（全国人大官方平台）的 MCP Server，提供现行有效法律、法规的全文检索与读取能力。

## 功能

- 🔍 **法规检索**：按名称、关键词搜索法律、行政法规、部门规章
- 📄 **全文获取**：读取法律法规全文（含历史沿革）
- 🗂️ **分类浏览**：按法律类别、效力层级、颁布机关浏览
- 🕐 **有效性查询**：查询法规当前有效状态、施行日期、修订记录
- 🔗 **关联法规**：查找与某部法律相关的配套法规、司法解释

## 数据来源

[国家法律法规数据库](https://flk.npc.gov.cn/)（全国人民代表大会官方平台，公开数据）

## 快速开始

```bash
pip install -r requirements.txt
cp config.example.py config.py
```

**Claude Desktop 配置（macOS）：**

```json
{
  "mcpServers": {
    "national-laws": {
      "command": "python",
      "args": ["/绝对路径/mcp-servers/chinese-legal/national-laws/server.py"]
    }
  }
}
```

## 可用工具（MCP Tools）

| 工具名 | 描述 | 核心参数 |
|--------|------|----------|
| `search_laws` | 搜索法律法规 | `keyword`, `category`, `level`, `status` |
| `get_law_full_text` | 获取法律全文 | `law_id` |
| `get_law_articles` | 获取指定条文 | `law_id`, `article_numbers` |
| `list_law_categories` | 列出法律类别 | — |

## 使用示例

> "查找《公司法》第一百八十二条到第一百九十条的内容"

> "搜索所有关于个人信息保护的现行有效法律法规"

> "《劳动合同法》最近一次修订是什么时候？修改了哪些内容？"
