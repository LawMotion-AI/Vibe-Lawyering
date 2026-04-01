# 合同审核技能 - XML 修订痕迹写入功能更新说明

## 更新日期
2026 年 3 月 19 日

## 更新概述

本次更新修改了合同审核技能的实现方式，**将修订和批注统一固定为直接通过 XML 底层操作写入**，确保与 WPS Office 完全兼容。

## 主要变更

### 1. 核心实现方式变更

**之前：**
- 依赖高层封装 API
- 修订痕迹可能无法在 WPS 中正确显示
- 对修订标记的控制能力有限

**现在：**
- 直接操作 DOCX 底层 XML 文件（document.xml, comments.xml, settings.xml）
- 严格遵循 ECMA-376 Office Open XML 标准
- 完全控制修订标记的格式和属性
- 确保 WPS 兼容性

### 2. 新增文件

#### 2.1 核心脚本

**`scripts/internal_write_revisions_xml.py`**
- WPSRevisionWriter 类：核心修订写入器
- 支持删除、插入、批注三种修订类型
- 自动管理修订 ID、时间戳、作者信息
- 自动启用修订跟踪设置

主要功能：
```python
# 创建修订写入器
with WPSRevisionWriter(input_path, output_path) as writer:
    # 添加删除标记
    writer.add_deletion("原内容", author="审核人", date="2026-03-19T10:00:00Z")
    
    # 添加插入标记
    writer.add_insertion("新内容", author="审核人", date="2026-03-19T10:00:00Z")
    
    # 添加批注
    comment_id = writer.add_comment("批注内容", author="审核人")
    
    # 完成并保存
    writer.finalize()
```

#### 2.2 参考文档

**`references/xml-revision-spec.md`**
- 详细的 XML 修订实现规范
- WPS 兼容性要求说明
- 完整的代码示例
- 常见问题解答

内容包括：
- DOCX 文件结构说明
- 修订标记 XML 结构（w:del, w:ins, w:comment 等）
- 命名空间声明要求
- 时间格式规范（ISO 8601）
- ID 唯一性管理
- 完整的实现步骤和代码示例

#### 2.3 示例脚本

**`scripts/example_usage.py`**
- 三个实用示例：
  1. 基本修订操作示例
  2. 合同审核场景示例
  3. 批量添加批注示例

**`scripts/test_xml_revision.py`**
- 自动化测试脚本
- 测试项目：
  - 基本修订功能
  - WPS 兼容性检查
  - XML 结构验证

#### 2.4 说明文档

**`README.md`**
- 技能使用说明
- XML 结构示例
- 实现流程说明
- 依赖和测试指南

### 3. SKILL.md 更新

**更新内容：**
- 在 description 中强调 XML 修订痕迹写入要求
- 新增"docx 文件 - 批注版 XML 实现规范"章节
- 详细说明 XML 修订痕迹写入规范
- 添加 WPS 兼容性要求
- 提供完整的 XML 示例代码
- 在定稿前检查和质量标准中增加 XML 相关要求

**新增章节：**
```markdown
### 1. docx 文件 - 批注版 XML 实现规范

**重要：修订版、批注版、修订批注版都必须通过直接操作 DOCX 底层 XML 写入修订和批注，确保 WPS 兼容性。**

#### XML 修订痕迹写入规范

1. 使用标准 Track Changes XML 结构
2. WPS 兼容性要求
3. XML 命名空间声明
4. 修订标记示例
5. comments.xml 结构
6. settings.xml 配置

#### 实现步骤

1. 解压 DOCX 文件
2. 解析 document.xml
3. 写入修订标记
4. 更新 comments.xml
5. 更新 settings.xml
6. 重新打包 DOCX
```

## 技术细节

### XML 命名空间

```xml
<w:document 
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
```

### 删除标记格式

```xml
<w:del w:author="审核人" w:date="2026-03-19T10:00:00Z" w:delId="1">
  <w:r>
    <w:t>被删除的文本内容</w:t>
  </w:r>
</w:del>
```

### 插入标记格式

```xml
<w:ins w:author="审核人" w:date="2026-03-19T10:00:00Z" w:insId="2">
  <w:r>
    <w:t>新插入的文本内容</w:t>
  </w:r>
</w:ins>
```

### 批注标记格式

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
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="101" w:author="审核人" w:date="2026-03-19T10:00:00Z">
    <w:p>
      <w:r>
        <w:t>批注内容文本</w:t>
      </w:r>
    </w:p>
  </w:comment>
</w:comments>
```

### 修订跟踪设置 (settings.xml)

```xml
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:trackRevisions w:val="1"/>
  <w:showRevisions w:val="1"/>
  <w:revisionView>
    <w:markup>1</w:markup>
  </w:revisionView>
</w:settings>
```

## WPS 兼容性保证

### 必须遵守的规则

1. **时间格式**：必须使用 ISO 8601 格式 `YYYY-MM-DDThh:mm:ssZ`
2. **唯一 ID**：每个修订的 ID 必须唯一且为正整数
3. **完整属性**：必须包含 author、date、delId/insId
4. **命名空间**：必须使用正确的 OOXML 命名空间
5. **启用跟踪**：必须在 settings.xml 中启用 trackRevisions 和 showRevisions

### 测试验证

生成的修订版 DOCX 必须在 WPS Office 中验证：
1. 打开文档
2. 检查"审阅"选项卡
3. 确认修订标记正确显示（删除线、下划线）
4. 确认批注正确显示在批注框中
5. 确认可以接受/拒绝修订

## 依赖库

## 使用方法

### 对外入口：只使用 PowerShell 包装器

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\run_generate_review_docx.ps1 `
  -Source "原合同.docx" `
  -Instructions ".\references\review-instructions.example.json" `
  -Output "原合同-修订批注版.docx"
```

### 内部实现与测试

- `scripts/internal_generate_review_docx.ps1`：内部 OOXML 直改实现
- `scripts/internal_write_revisions_xml.py`：内部 Python 实现与算法验证
- `scripts/test_xml_revision.py`：Python 内部回归测试
- `scripts/test_cross_entry_consistency.py`：PowerShell / Python 一致性测试

## 文件结构

```
contract-review-docx-auditor/
├── SKILL.md                          # 技能主文档（已更新）
├── README.md                         # 使用说明（新增）
├── CHANGELOG.md                      # 更新说明（本文件，新增）
├── scripts/
│   ├── run_generate_review_docx.ps1  # 对外唯一入口
│   ├── internal_generate_review_docx.ps1
│   ├── internal_stage_review_inputs.ps1
│   ├── internal_write_revisions_xml.py
│   └── test_xml_revision.py          # 内部测试脚本
└── references/
    └── xml-revision-spec.md          # XML 实现规范（新增）
```

## 优势对比

### 之前的方式
- ❌ 依赖高层封装 API
- ❌ 修订痕迹可能无法在 WPS 中显示
- ❌ 对 XML 结构控制能力弱
- ❌ 兼容性无法保证

### 现在的方式
- ✅ 直接操作底层 XML
- ✅ 严格遵循 ECMA-376 标准
- ✅ 完全控制修订标记格式
- ✅ 确保 WPS 兼容性
- ✅ 可精确管理修订 ID、时间戳、作者信息
- ✅ 可自定义批注内容和格式

## 注意事项

1. **输入文件必须是有效的 DOCX**：不能是加密或损坏的文件
2. **修订 ID 自动管理**：使用内部计数器确保唯一性
3. **时间使用 UTC**：所有时间戳都转换为 UTC 时间
4. **临时文件清理**：使用上下文管理器自动清理临时文件
5. **XML 编码**：统一使用 UTF-8 编码

## 后续计划

1. 增加对更多修订类型的支持（格式修改、移动等）
2. 添加对表格、图片等复杂元素的支持
3. 提供更高阶的 API 简化使用
4. 增加批量处理能力
5. 添加修订对比功能

## 参考资源

- [ECMA-376 Office Open XML 标准](http://www.ecma-international.org/publications/standards/Ecma-376.htm)
- [ISO/IEC 29500](https://www.iso.org/standard/71691.html)
- [Microsoft Office Open XML Schema Reference](https://docs.microsoft.com/en-us/office/open-xml/open-xml-sdk)
- `references/xml-revision-spec.md` - 详细实现规范

## 联系方式

如有问题或建议，请参考文档或运行测试脚本验证功能。

---

**更新完成日期**: 2026 年 3 月 19 日  
**版本**: v2.0 - XML 修订痕迹写入版本
