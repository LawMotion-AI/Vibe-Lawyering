# DOCX 修订痕迹 XML 实现规范

## 概述

本文档详细说明如何通过直接操作 DOCX 底层 XML 来写入修订痕迹，确保与 WPS 完全兼容。

## DOCX 文件结构

DOCX 文件本质是一个 ZIP 压缩包，包含以下核心文件：

```
document.docx/
├── [Content_Types].xml          # 内容类型定义
├── _rels/
│   └── .rels                    # 包关系定义
├── word/
│   ├── document.xml             # 主文档内容
│   ├── comments.xml             # 批注内容
│   ├── settings.xml             # 文档设置
│   ├── styles.xml               # 样式定义
│   ├── _rels/
│   │   └── document.xml.rels    # 文档关系
│   └── theme/
│       └── theme1.xml           # 主题定义
└── docProps/
    ├── app.xml                  # 应用程序属性
    └── core.xml                 # 核心属性
```

## 修订痕迹的核心 XML 元素

### 1. 删除标记 (w:del)

```xml
<w:p>
  <w:r>
    <w:del w:author="审核人" w:date="2026-03-19T10:00:00Z" w:id="1">
      <w:t>被删除的文本内容</w:t>
    </w:del>
  </w:r>
</w:p>
```

**属性说明：**
- `w:author`: 删除操作的作者姓名
- `w:date`: 删除时间，ISO 8601 格式
- `w:delId`: 删除操作的唯一标识符（正整数）

### 2. 插入标记 (w:ins)

```xml
<w:p>
  <w:r>
    <w:ins w:author="审核人" w:date="2026-03-19T10:00:00Z" w:id="2">
      <w:t>新插入的文本内容</w:t>
    </w:ins>
  </w:r>
</w:p>
```

**属性说明：**
- `w:author`: 插入操作的作者姓名
- `w:date`: 插入时间，ISO 8601 格式
- `w:insId`: 插入操作的唯一标识符（正整数）

### 3. 批注范围标记

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

**元素说明：**
- `w:commentRangeStart`: 批注范围开始标记
- `w:commentRangeEnd`: 批注范围结束标记
- `w:commentReference`: 批注引用标记（显示为批注图标）
- `w:id`: 批注的唯一标识符（正整数）

### 4. 批注内容 (comments.xml)

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
        <w:t>建议：修改为"违约方应承担因其违约行为给守约方造成的全部直接损失"</w:t>
      </w:r>
    </w:p>
  </w:comment>
</w:comments>
```

### 5. 修订跟踪设置 (settings.xml)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <!-- 启用修订跟踪 -->
  <w:trackRevisions w:val="1"/>
  
  <!-- 显示修订标记 -->
  <w:showRevisions w:val="1"/>
  
  <!-- 修订视图设置 -->
  <w:revisionView>
    <w:markup>1</w:markup>
  </w:revisionView>
  
  <!-- 其他设置... -->
</w:settings>
```

## WPS 兼容性要求

### 1. 命名空间声明

文档根元素必须包含以下命名空间声明：

```xml
<w:document 
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
```

### 2. 时间格式

所有时间戳必须使用 ISO 8601 格式：
- 格式：`YYYY-MM-DDThh:mm:ssZ`
- 示例：`2026-03-19T10:00:00Z`
- 必须使用 UTC 时间（末尾的 Z 表示零时区）

### 3. ID 唯一性

- `w:id`：修订操作 ID（删除/插入），必须是唯一正整数
- `w:id` (comment): 批注 ID，必须是唯一正整数

建议从 1 开始递增分配。

### 4. 作者信息

- `w:author` 属性必须填写完整的作者姓名
- 建议使用中文姓名（如"合同审核人"）
- 不要使用空字符串或占位符

### 5. 修订标记完整性

每个修订标记必须包含：
- 作者信息 (`w:author`)
- 时间戳 (`w:date`)
- 唯一 ID (`w:id`)

缺少任何一项都可能导致 WPS 无法正确识别修订。

## 实现步骤

### 步骤 1: 解压 DOCX

```python
import zipfile

def extract_docx(docx_path, extract_to):
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
```

### 步骤 2: 解析 document.xml

```python
from lxml import etree

def load_document(xml_path):
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.parse(xml_path, parser)
```

### 步骤 3: 创建修订标记

```python
def create_del_element(text, author, date, del_id):
    w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    del_elem = etree.Element(f'{w_ns}del')
    del_elem.set(f'{w_ns}author', author)
    del_elem.set(f'{w_ns}date', date)
    del_elem.set(f'{w_ns}delId', str(del_id))
    
    run_elem = etree.Element(f'{w_ns}r')
    text_elem = etree.Element(f'{w_ns}t')
    text_elem.text = text
    
    run_elem.append(text_elem)
    del_elem.append(run_elem)
    
    return del_elem
```

### 步骤 4: 替换原文本

```python
def replace_with_revision(paragraph, old_text, new_text, author, date):
    w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    # 查找包含旧文本的 run
    for run in paragraph.iter(f'{w_ns}r'):
        text_elem = run.find(f'{w_ns}t')
        if text_elem is not None and text_elem.text == old_text:
            # 创建删除标记
            del_elem = create_del_element(old_text, author, date, del_id=1)
            
            # 创建插入标记
            ins_elem = create_ins_element(new_text, author, date, ins_id=2)
            
            # 替换原文本
            run.addprevious(del_elem)
            run.addnext(ins_elem)
            
            # 删除原文本节点
            run.remove(text_elem)
            break
```

### 步骤 5: 添加批注

```python
def add_comment(comments_tree, comment_id, author, date, comment_text):
    w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    comments_root = comments_tree.getroot()
    
    comment_elem = etree.Element(f'{w_ns}comment')
    comment_elem.set(f'{w_ns}id', str(comment_id))
    comment_elem.set(f'{w_ns}author', author)
    comment_elem.set(f'{w_ns}date', date)
    
    # 添加批注段落
    para_elem = etree.Element(f'{w_ns}p')
    run_elem = etree.Element(f'{w_ns}r')
    text_elem = etree.Element(f'{w_ns}t')
    text_elem.text = comment_text
    
    run_elem.append(text_elem)
    para_elem.append(run_elem)
    comment_elem.append(para_elem)
    
    comments_root.append(comment_elem)
```

### 步骤 5.1: 更新文档关系 (document.xml.rels)

```python
def update_document_rels(rels_path):
    """更新 document.xml.rels，添加对 comments.xml 的引用"""
    if not os.path.exists(rels_path):
        return
    
    # 解析关系文件
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(rels_path, parser)
    root = tree.getroot()
    
    # 检查是否已有 comments.xml 引用
    has_comments = any(rel.get('Target') == 'comments.xml' for rel in root.findall('./Relationship'))
    
    if not has_comments:
        # 生成新的 rId
        max_id = max(int(rel.get('Id')[3:]) for rel in root.findall('./Relationship') 
                    if rel.get('Id', '').startswith('rId'))
        new_id = f'rId{max_id + 1}'
        
        # 创建新的关系
        new_rel = etree.Element('Relationship')
        new_rel.set('Id', new_id)
        new_rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments')
        new_rel.set('Target', 'comments.xml')
        root.append(new_rel)
        
        # 保存文件
        tree.write(rels_path, xml_declaration=True, encoding='UTF-8', standalone='yes')
```

### 步骤 6: 启用修订跟踪

```python
def enable_track_revisions(settings_tree):
    w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    settings_root = settings_tree.getroot()
    
    # 添加 trackRevisions
    track_elem = etree.Element(f'{w_ns}trackRevisions')
    track_elem.set(f'{w_ns}val', '1')
    settings_root.append(track_elem)
    
    # 添加 showRevisions
    show_elem = etree.Element(f'{w_ns}showRevisions')
    show_elem.set(f'{w_ns}val', '1')
    settings_root.append(show_elem)
    
    # 添加 revisionView
    revision_view_elem = etree.Element(f'{w_ns}revisionView')
    markup_elem = etree.Element(f'{w_ns}markup')
    markup_elem.text = '1'
    revision_view_elem.append(markup_elem)
    settings_root.append(revision_view_elem)
```

### 步骤 7: 重新打包 DOCX

```python
import os

def create_docx(source_dir, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                arcname = arcname.replace(os.sep, '/')
                zip_ref.write(file_path, arcname)
```

## 完整示例

```python
from lxml import etree
import zipfile
import tempfile
import os
from datetime import datetime

class WPSRevisionWriter:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.temp_dir = tempfile.mkdtemp()
        self.del_id = 1
        self.ins_id = 1
        self.comment_id = 1
    
    def extract(self):
        with zipfile.ZipFile(self.input_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
    
    def save(self):
        with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    arcname = arcname.replace(os.sep, '/')
                    zip_ref.write(file_path, arcname)
    
    def add_revision(self, paragraph_index, old_text, new_text, comment=None):
        doc_path = os.path.join(self.temp_dir, 'word', 'document.xml')
        doc_tree = etree.parse(doc_path)
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        paragraphs = doc_tree.findall(f'.//{w_ns}p')
        
        if paragraph_index < len(paragraphs):
            para = paragraphs[paragraph_index]
            date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # 查找并替换文本
            for run in para.iter(f'{w_ns}r'):
                text_elem = run.find(f'{w_ns}t')
                if text_elem is not None and text_elem.text == old_text:
                    # 创建删除标记
                    del_elem = etree.Element(f'{w_ns}del')
                    del_elem.set(f'{w_ns}author', '合同审核人')
                    del_elem.set(f'{w_ns}date', date)
                    del_elem.set(f'{w_ns}delId', str(self.del_id))
                    self.del_id += 1
                    
                    del_run = etree.Element(f'{w_ns}r')
                    del_text = etree.Element(f'{w_ns}t')
                    del_text.text = old_text
                    del_run.append(del_text)
                    del_elem.append(del_run)
                    
                    # 创建插入标记
                    ins_elem = etree.Element(f'{w_ns}ins')
                    ins_elem.set(f'{w_ns}author', '合同审核人')
                    ins_elem.set(f'{w_ns}date', date)
                    ins_elem.set(f'{w_ns}insId', str(self.ins_id))
                    self.ins_id += 1
                    
                    ins_run = etree.Element(f'{w_ns}r')
                    ins_text = etree.Element(f'{w_ns}t')
                    ins_text.text = new_text
                    ins_run.append(ins_text)
                    ins_elem.append(ins_run)
                    
                    # 替换
                    run.addprevious(del_elem)
                    run.addnext(ins_elem)
                    run.remove(text_elem)
                    break
            
            doc_tree.write(doc_path, xml_declaration=True, encoding='UTF-8', standalone='yes')
        
        # 添加批注
        if comment:
            self.add_comment(paragraph_index, comment)
    
    def add_comment(self, paragraph_index, comment_text):
        comments_path = os.path.join(self.temp_dir, 'word', 'comments.xml')
        
        # 创建或加载 comments.xml
        if os.path.exists(comments_path):
            comments_tree = etree.parse(comments_path)
        else:
            w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            root = etree.Element(f'{w_ns}comments')
            comments_tree = etree.ElementTree(root)
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        comments_root = comments_tree.getroot()
        
        comment_elem = etree.Element(f'{w_ns}comment')
        comment_elem.set(f'{w_ns}id', str(self.comment_id))
        comment_elem.set(f'{w_ns}author', '合同审核人')
        comment_elem.set(f'{w_ns}date', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
        
        para_elem = etree.Element(f'{w_ns}p')
        run_elem = etree.Element(f'{w_ns}r')
        text_elem = etree.Element(f'{w_ns}t')
        text_elem.text = comment_text
        
        run_elem.append(text_elem)
        para_elem.append(run_elem)
        comment_elem.append(para_elem)
        comments_root.append(comment_elem)
        
        comments_tree.write(comments_path, xml_declaration=True, encoding='UTF-8', standalone='yes')
        self.comment_id += 1
    
    def enable_revisions(self):
        settings_path = os.path.join(self.temp_dir, 'word', 'settings.xml')
        
        if os.path.exists(settings_path):
            settings_tree = etree.parse(settings_path)
        else:
            w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            root = etree.Element(f'{w_ns}settings')
            settings_tree = etree.ElementTree(root)
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        settings_root = settings_tree.getroot()
        
        # trackRevisions
        track_elem = etree.Element(f'{w_ns}trackRevisions')
        track_elem.set(f'{w_ns}val', '1')
        settings_root.append(track_elem)
        
        # showRevisions
        show_elem = etree.Element(f'{w_ns}showRevisions')
        show_elem.set(f'{w_ns}val', '1')
        settings_root.append(show_elem)
        
        settings_tree.write(settings_path, xml_declaration=True, encoding='UTF-8', standalone='yes')
    
    def finalize(self):
        self.enable_revisions()
        self.save()

# 使用示例
writer = WPSRevisionWriter('input.docx', 'output.docx')
writer.extract()
writer.add_revision(0, '原条款', '修订后条款', '批注内容')
writer.finalize()
```

## 常见问题

### Q1: WPS 无法显示修订标记

**原因：**
1. settings.xml 中未启用 trackRevisions
2. 修订标记缺少必要属性（author、date、delId/insId）
3. 时间格式不正确

**解决方案：**
确保所有修订标记完整，并启用修订跟踪。

### Q2: 批注不显示

**原因：**
1. comments.xml 格式错误
2. 批注 ID 与 document.xml 中的范围标记不匹配
3. 缺少 commentRangeStart 或 commentRangeEnd

**解决方案：**
检查 comments.xml 的 XML 结构，确保 ID 匹配。

### Q3: 修订 ID 冲突

**原因：**
多个修订使用了相同的 ID

**解决方案：**
使用递增计数器确保 ID 唯一性。

## 参考标准

- [ECMA-376 Office Open XML](http://www.ecma-international.org/publications/standards/Ecma-376.htm)
- [ISO/IEC 29500](https://www.iso.org/standard/71691.html)
- [Microsoft Office Open XML Schema Reference](https://docs.microsoft.com/en-us/office/open-xml/open-xml-sdk)

## 测试验证

生成修订版 DOCX 后，必须在以下软件中测试：

1. **WPS Office** (最新版本)
   - 打开文档
   - 检查"审阅"选项卡
   - 确认修订标记正确显示
   - 确认批注正确显示

2. **Microsoft Word** (可选)
   - 验证兼容性

3. **LibreOffice Writer** (可选)
   - 验证开源兼容性

## 总结

通过直接操作 DOCX 底层 XML 写入修订痕迹，可以确保：
- 完全控制修订标记格式
- 与 WPS 完美兼容
- 避免依赖高级 API 的局限性

关键要点：
1. 严格遵守 OOXML 标准
2. 确保所有必要属性完整
3. 使用正确的时间格式
4. 保持 ID 唯一性
5. 在 settings.xml 中启用修订跟踪
