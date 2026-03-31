# 合同审核技能 - XML 修订痕迹写入

## 概述

本技能用于中文合同审核与修改，修订和批注均通过直接操作 DOCX 底层 XML 写入，且该实现路径固定不变，确保与 WPS 完全兼容。

## 核心特性

### 1. XML 修订痕迹写入

- **直接操作底层 XML**：不依赖高层封装接口，直接编辑 document.xml、comments.xml、settings.xml
- **修订和批注都走 XML**：删除、插入、批注范围、批注正文全部通过 XML 节点写入，不提供非 XML 备选路径
- **WPS 完全兼容**：严格遵循 ECMA-376 Office Open XML 标准
- **标准修订标记**：使用 `<w:del>`、`<w:ins>`、`<w:commentRangeStart>` 等标准元素
- **完整修订信息**：包含作者、时间、唯一 ID 等必要属性

### 2. 修订类型支持

- **删除标记** (`<w:del>`)：标记被删除的文本
- **插入标记** (`<w:ins>`)：标记新插入的文本
- **批注标记** (`<w:comment>`)：添加批注说明

### 3. WPS 兼容性保证

- 使用标准 OOXML 命名空间
- ISO 8601 时间格式
- 唯一修订 ID 管理
- 自动启用修订跟踪设置

## 使用方法

### 基本用法

```python
from scripts.write_revisions_xml import WPSRevisionWriter

# 创建修订写入器
with WPSRevisionWriter('input.docx', 'output.docx') as writer:
    # 添加删除标记
    del_xml = writer.add_deletion('原条款内容')
    
    # 添加插入标记
    ins_xml = writer.add_insertion('修订后条款内容')
    
    # 添加批注
    comment_id = writer.add_comment('问题描述 + 风险分析 + 修改建议')
    
    # 完成并保存
    writer.finalize()
```

### 从 JSON 配置创建修订

```python
from scripts.write_revisions_xml import create_revision_from_json
import json

revisions = [
    {
        'type': 'delete',
        'text': '原条款内容',
        'location': {'paragraph': 1, 'run': 0}
    },
    {
        'type': 'insert',
        'text': '修订后条款内容',
        'location': {'paragraph': 1, 'run': 0}
    },
    {
        'type': 'comment',
        'text': '需要批注的文本',
        'comment': '问题：该条款存在法律风险\n风险：可能导致违约责任不清\n建议：修改为...',
        'location': {'paragraph': 2, 'run': 1}
    }
]

create_revision_from_json(
    'input.docx',
    'output.docx',
    json.dumps(revisions, ensure_ascii=False)
)
```

## XML 结构示例

### 删除标记

```xml
<w:p>
  <w:r>
    <w:del w:author="审核人" w:date="2026-03-19T10:00:00Z" w:delId="1">
      <w:t>被删除的文本内容</w:t>
    </w:del>
  </w:r>
</w:p>
```

### 插入标记

```xml
<w:p>
  <w:r>
    <w:ins w:author="审核人" w:date="2026-03-19T10:00:00Z" w:insId="2">
      <w:t>新插入的文本内容</w:t>
    </w:ins>
  </w:r>
</w:p>
```

### 批注标记

```xml
<w:p>
  <w:commentRangeStart w:id="101"/>
  <w:r>
    <w:t>需要批注的文本</w:t>
  </w:r>
  <w:commentRangeEnd w:id="101"/>
  <w:r>
    <w:commentReference w:id="101"/>
  </w:r>
</w:p>
```

### 批注内容 (comments.xml)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="101" w:author="审核人" w:date="2026-03-19T10:00:00Z">
    <w:p>
      <w:r>
        <w:t>问题：该条款责任边界不清</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>风险：可能导致违约责任无法明确划分</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>建议：修改为"违约方应承担全部直接损失"</w:t>
      </w:r>
    </w:p>
  </w:comment>
</w:comments>
```

### 修订跟踪设置 (settings.xml)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:trackRevisions w:val="1"/>
  <w:showRevisions w:val="1"/>
  <w:revisionView>
    <w:markup>1</w:markup>
  </w:revisionView>
</w:settings>
```

## 实现流程

1. **解压 DOCX**：将 DOCX 文件解压到临时目录
2. **解析 XML**：读取 document.xml、comments.xml、settings.xml
3. **写入修订**：
   - 查找目标文本位置
   - 创建 `<w:del>` 或 `<w:ins>` 标记
   - 添加批注范围标记和引用
4. **更新批注**：在 comments.xml 中添加批注内容
5. **启用跟踪**：在 settings.xml 中启用修订跟踪
6. **重新打包**：将修改后的文件重新打包为 DOCX

## 依赖库

```bash
pip install lxml
```

## 文件结构

```
contract-review-docx-auditor/
├── SKILL.md                          # 技能主文档
├── scripts/
│   └── write_revisions_xml.py        # XML 修订写入脚本
├── references/
│   └── xml-revision-spec.md          # XML 实现详细规范
└── README.md                         # 本文件
```

## WPS 兼容性测试

生成修订版 DOCX 后，必须在 WPS Office 中验证：

1. 打开生成的 DOCX 文件
2. 点击"审阅"选项卡
3. 确认所有修订标记正确显示（删除线、下划线等）
4. 确认所有批注正确显示在批注框中
5. 确认可以接受/拒绝修订

## 注意事项

### 必须遵守的规则

1. **时间格式**：必须使用 ISO 8601 格式 `YYYY-MM-DDThh:mm:ssZ`
2. **唯一 ID**：每个修订的 ID 必须唯一且为正整数
3. **完整属性**：必须包含 author、date、delId/insId
4. **命名空间**：必须使用正确的 OOXML 命名空间
5. **启用跟踪**：必须在 settings.xml 中启用 trackRevisions

### 常见错误

1. **WPS 不显示修订**：
   - 检查 settings.xml 是否启用 trackRevisions
   - 检查修订标记属性是否完整

2. **批注不显示**：
   - 检查 comments.xml 格式是否正确
   - 检查批注 ID 是否匹配

3. **XML 解析错误**：
   - 检查命名空间声明是否正确
   - 检查 XML 是否符合 Well-Formed 要求

## 参考文档

- [xml-revision-spec.md](references/xml-revision-spec.md) - 详细实现规范
- [SKILL.md](SKILL.md) - 技能完整说明
- [ECMA-376 标准](http://www.ecma-international.org/publications/standards/Ecma-376.htm)
- [ISO/IEC 29500](https://www.iso.org/standard/71691.html)

## 技术支持

如遇到问题，请检查：
1. XML 结构是否符合 ECMA-376 标准
2. 所有必要属性是否完整
3. WPS 是否为最新版本
4. 修订 ID 是否唯一

## 许可证

本技能仅供学习和研究使用。
