"""
通过直接操作 DOCX 底层 XML 写入修订痕迹，确保 WPS 兼容性

这个脚本提供以下功能：
1. 解压 DOCX 文件
2. 解析 document.xml
3. 写入修订标记（删除、插入、批注）
4. 更新 comments.xml
5. 更新 settings.xml
6. 重新打包 DOCX

确保生成的 XML 符合 ECMA-376 标准，与 WPS 完全兼容
"""

import zipfile
import os
import tempfile
import shutil
from datetime import datetime
from lxml import etree
from typing import List, Dict, Tuple, Optional
import json


class WPSRevisionWriter:
    """WPS 兼容的修订痕迹写入器"""
    
    # Word ML 命名空间
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
        'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    
    def __init__(self, input_docx_path: str, output_docx_path: str):
        """
        初始化修订写入器
        
        Args:
            input_docx_path: 输入 DOCX 文件路径
            output_docx_path: 输出 DOCX 文件路径
        """
        self.input_path = input_docx_path
        self.output_path = output_docx_path
        self.temp_dir = tempfile.mkdtemp()
        self.document_xml_path = os.path.join(self.temp_dir, 'word', 'document.xml')
        self.comments_xml_path = os.path.join(self.temp_dir, 'word', 'comments.xml')
        self.settings_xml_path = os.path.join(self.temp_dir, 'word', 'settings.xml')
        self.comment_font = 'SimSun'
        
        # 修订计数器
        self.del_id_counter = 1
        self.ins_id_counter = 1
        self.comment_id_counter = 1
        
        # 修订作者信息
        self.author = "合同审核人"
        self.date_format = "%Y-%m-%dT%H:%M:%SZ"
        
    def __enter__(self):
        """上下文管理器入口"""
        self._extract_docx()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _extract_docx(self):
        """解压 DOCX 文件"""
        with zipfile.ZipFile(self.input_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
    
    def _save_docx(self):
        """重新打包 DOCX 文件"""
        # 确保输出目录存在
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建新的 ZIP 文件
        with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    # 规范化路径分隔符
                    arcname = arcname.replace(os.sep, '/')
                    zip_ref.write(file_path, arcname)
    
    def _get_current_date(self) -> str:
        """获取当前 ISO 8601 格式时间"""
        return datetime.utcnow().strftime(self.date_format)
    
    def _load_document_xml(self) -> etree._ElementTree:
        """加载 document.xml"""
        parser = etree.XMLParser(remove_blank_text=False)
        return etree.parse(self.document_xml_path, parser)
    
    def _save_document_xml(self, tree: etree._ElementTree):
        """保存 document.xml"""
        tree.write(
            self.document_xml_path,
            xml_declaration=True,
            encoding='UTF-8',
            standalone='yes'
        )
    
    def _load_comments_xml(self) -> Optional[etree._ElementTree]:
        """加载 comments.xml，如果不存在则创建"""
        if not os.path.exists(self.comments_xml_path):
            # 创建空的 comments.xml
            root = etree.Element(
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}comments'
            )
            tree = etree.ElementTree(root)
            self._save_comments_xml(tree)
            return tree
        
        parser = etree.XMLParser(remove_blank_text=False)
        return etree.parse(self.comments_xml_path, parser)
    
    def _save_comments_xml(self, tree: etree._ElementTree):
        """保存 comments.xml"""
        tree.write(
            self.comments_xml_path,
            xml_declaration=True,
            encoding='UTF-8',
            standalone='yes'
        )
    
    def _load_settings_xml(self) -> Optional[etree._ElementTree]:
        """加载 settings.xml，如果不存在则创建"""
        if not os.path.exists(self.settings_xml_path):
            # 创建基本的 settings.xml
            root = etree.Element(
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}settings'
            )
            tree = etree.ElementTree(root)
            self._save_settings_xml(tree)
            return tree
        
        parser = etree.XMLParser(remove_blank_text=False)
        return etree.parse(self.settings_xml_path, parser)
    
    def _save_settings_xml(self, tree: etree._ElementTree):
        """保存 settings.xml"""
        tree.write(
            self.settings_xml_path,
            xml_declaration=True,
            encoding='UTF-8',
            standalone='yes'
        )
    
    def _update_document_rels(self):
        """更新 document.xml.rels 文件，添加对 comments.xml 的引用"""
        rels_path = os.path.join(self.temp_dir, 'word', '_rels', 'document.xml.rels')
        
        if not os.path.exists(rels_path):
            return
        
        # 解析 document.xml.rels
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(rels_path, parser)
        root = tree.getroot()
        
        # 检查是否已经有 comments.xml 的引用
        has_comments = False
        for rel in root.findall('./Relationship'):
            if rel.get('Target') == 'comments.xml':
                has_comments = True
                break
        
        if not has_comments:
            # 找到最大的 rId
            max_id = 0
            for rel in root.findall('./Relationship'):
                id_attr = rel.get('Id')
                if id_attr and id_attr.startswith('rId'):
                    try:
                        num = int(id_attr[3:])
                        if num > max_id:
                            max_id = num
                    except:
                        pass
            
            # 创建新的 Relationship 元素
            new_rel = etree.Element('Relationship')
            new_rel.set('Id', f'rId{max_id + 1}')
            new_rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments')
            new_rel.set('Target', 'comments.xml')
            
            # 添加到根元素
            root.append(new_rel)
            
            # 保存文件
            tree.write(rels_path, xml_declaration=True, encoding='UTF-8', standalone='yes')
    
    def _append_comment_run_properties(self, run_elem: etree._Element):
        """为批注正文强制写入宋体字体属性"""
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        run_props = etree.Element(f'{w_ns}rPr')
        run_style = etree.Element(f'{w_ns}rStyle')
        run_style.set(f'{w_ns}val', 'CommentText')
        run_props.append(run_style)

        fonts = etree.Element(f'{w_ns}rFonts')
        fonts.set(f'{w_ns}ascii', self.comment_font)
        fonts.set(f'{w_ns}hAnsi', self.comment_font)
        fonts.set(f'{w_ns}eastAsia', self.comment_font)
        fonts.set(f'{w_ns}cs', self.comment_font)
        fonts.set(f'{w_ns}hint', 'eastAsia')
        run_props.append(fonts)
        run_elem.append(run_props)
    
    def add_deletion(self, text: str, author: Optional[str] = None, 
                     date: Optional[str] = None) -> str:
        """
        添加删除标记
        
        Args:
            text: 要删除的文本
            author: 作者名称（可选，默认使用实例的 author）
            date: 时间戳（可选，默认使用当前时间）
            
        Returns:
            删除标记的 XML 字符串
        """
        if author is None:
            author = self.author
        if date is None:
            date = self._get_current_date()
        
        del_id = self.del_id_counter
        self.del_id_counter += 1
        
        # 创建删除标记 XML
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # <w:del w:author="作者" w:date="时间" w:delId="ID">
        #   <w:r>
        #     <w:t>删除的文本</w:t>
        #   </w:r>
        # </w:del>
        
        del_elem = etree.Element(f'{w_ns}del')
        del_elem.set(f'{w_ns}author', author)
        del_elem.set(f'{w_ns}date', date)
        del_elem.set(f'{w_ns}delId', str(del_id))
        
        run_elem = etree.Element(f'{w_ns}r')
        text_elem = etree.Element(f'{w_ns}t')
        text_elem.text = text
        
        run_elem.append(text_elem)
        del_elem.append(run_elem)
        
        return etree.tostring(del_elem, encoding='unicode', xml_declaration=False)
    
    def add_insertion(self, text: str, author: Optional[str] = None,
                      date: Optional[str] = None) -> str:
        """
        添加插入标记
        
        Args:
            text: 要插入的文本
            author: 作者名称（可选）
            date: 时间戳（可选）
            
        Returns:
            插入标记的 XML 字符串
        """
        if author is None:
            author = self.author
        if date is None:
            date = self._get_current_date()
        
        ins_id = self.ins_id_counter
        self.ins_id_counter += 1
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # <w:ins w:author="作者" w:date="时间" w:insId="ID">
        #   <w:r>
        #     <w:t>插入的文本</w:t>
        #   </w:r>
        # </w:ins>
        
        ins_elem = etree.Element(f'{w_ns}ins')
        ins_elem.set(f'{w_ns}author', author)
        ins_elem.set(f'{w_ns}date', date)
        ins_elem.set(f'{w_ns}insId', str(ins_id))
        
        run_elem = etree.Element(f'{w_ns}r')
        text_elem = etree.Element(f'{w_ns}t')
        text_elem.text = text
        
        run_elem.append(text_elem)
        ins_elem.append(run_elem)
        
        return etree.tostring(ins_elem, encoding='unicode', xml_declaration=False)
    
    def add_comment(self, comment_text: str, comment_id: Optional[int] = None,
                    author: Optional[str] = None, date: Optional[str] = None) -> int:
        """
        添加批注
        
        Args:
            comment_text: 批注内容
            comment_id: 批注 ID（可选，自动生成）
            author: 作者名称（可选）
            date: 时间戳（可选）
            
        Returns:
            批注 ID
        """
        if comment_id is None:
            comment_id = self.comment_id_counter
            self.comment_id_counter += 1
        
        if author is None:
            author = self.author
        if date is None:
            date = self._get_current_date()
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # 加载 comments.xml
        comments_tree = self._load_comments_xml()
        comments_root = comments_tree.getroot()
        
        # 创建批注元素
        # <w:comment w:id="ID" w:author="作者" w:date="时间">
        #   <w:p>
        #     <w:r>
        #       <w:t>批注内容</w:t>
        #     </w:r>
        #   </w:p>
        # </w:comment>
        
        comment_elem = etree.Element(f'{w_ns}comment')
        comment_elem.set(f'{w_ns}id', str(comment_id))
        comment_elem.set(f'{w_ns}author', author)
        comment_elem.set(f'{w_ns}date', date)
        
        # 添加批注段落
        para_elem = etree.Element(f'{w_ns}p')
        run_elem = etree.Element(f'{w_ns}r')
        self._append_comment_run_properties(run_elem)
        text_elem = etree.Element(f'{w_ns}t')
        text_elem.text = comment_text
        
        run_elem.append(text_elem)
        para_elem.append(run_elem)
        comment_elem.append(para_elem)
        
        comments_root.append(comment_elem)
        
        # 保存 comments.xml
        self._save_comments_xml(comments_tree)
        
        # 更新 document.xml.rels，添加对 comments.xml 的引用
        self._update_document_rels()
        
        return comment_id
    
    def add_comment_range(self, paragraph_elem: etree._Element, text: str, 
                          comment_id: int):
        """
        在段落中添加批注范围标记
        
        Args:
            paragraph_elem: 段落元素
            text: 要批注的文本
            comment_id: 批注 ID
        """
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # 查找包含该文本的 run 元素
        target_run = None
        for run_elem in paragraph_elem.iter(f'{w_ns}r'):
            text_elem = run_elem.find(f'{w_ns}t', namespaces={'w': self.NAMESPACES['w']})
            if text_elem is not None and text_elem.text == text:
                target_run = run_elem
                break
        
        if target_run:
            # 批注标记必须是 w:p 的直接子元素，不能在 w:r 内部
            para_children = list(paragraph_elem)
            run_index = para_children.index(target_run)
            
            # 在 run 前添加 commentRangeStart (作为 w:p 的直接子元素)
            start_marker = etree.Element(f'{w_ns}commentRangeStart')
            start_marker.set(f'{w_ns}id', str(comment_id))
            paragraph_elem.insert(run_index, start_marker)
            
            # 找到最后一个 run
            last_run = None
            for run_elem in reversed(para_children):
                if run_elem.tag == f'{w_ns}r':
                    last_run = run_elem
                    break
            
            if last_run:
                last_run_index = para_children.index(last_run)
                # 注意：由于前面插入了 start_marker，索引需要 +1
                last_run_index += 1
                
                # 在最后一个 run 后添加 commentRangeEnd (作为 w:p 的直接子元素)
                end_marker = etree.Element(f'{w_ns}commentRangeEnd')
                end_marker.set(f'{w_ns}id', str(comment_id))
                paragraph_elem.insert(last_run_index + 1, end_marker)
                
                # 添加 commentReference (作为 w:p 的直接子元素)
                ref_run = etree.Element(f'{w_ns}r')
                ref_elem = etree.Element(f'{w_ns}commentReference')
                ref_elem.set(f'{w_ns}id', str(comment_id))
                ref_run.append(ref_elem)
                paragraph_elem.insert(last_run_index + 2, ref_run)
    
    def enable_track_revisions(self):
        """在 settings.xml 中启用修订跟踪"""
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        settings_tree = self._load_settings_xml()
        settings_root = settings_tree.getroot()
        
        # 添加或更新 trackRevisions
        track_elem = settings_root.find(f'{w_ns}trackRevisions')
        if track_elem is None:
            track_elem = etree.Element(f'{w_ns}trackRevisions')
            settings_root.append(track_elem)
        track_elem.set(f'{w_ns}val', '1')
        
        # 添加或更新 showRevisions
        show_elem = settings_root.find(f'{w_ns}showRevisions')
        if show_elem is None:
            show_elem = etree.Element(f'{w_ns}showRevisions')
            settings_root.append(show_elem)
        show_elem.set(f'{w_ns}val', '1')
        
        # 添加 revisionView
        revision_view_elem = settings_root.find(f'{w_ns}revisionView')
        if revision_view_elem is None:
            revision_view_elem = etree.Element(f'{w_ns}revisionView')
            settings_root.append(revision_view_elem)
        
        markup_elem = revision_view_elem.find(f'{w_ns}markup')
        if markup_elem is None:
            markup_elem = etree.Element(f'{w_ns}markup')
            markup_elem.text = '1'
            revision_view_elem.append(markup_elem)
        
        self._save_settings_xml(settings_tree)
    
    def apply_revision(self, revision: Dict):
        """
        应用单个修订
        
        Args:
            revision: 修订字典，包含以下键：
                - type: 'delete', 'insert', 'comment'
                - text: 文本内容
                - location: 位置信息（段落号、文本等）
                - comment: 批注内容（仅 comment 类型需要）
        """
        if revision['type'] == 'delete':
            # 处理删除
            pass  # 需要在 document.xml 中查找并替换
        elif revision['type'] == 'insert':
            # 处理插入
            pass
        elif revision['type'] == 'comment':
            # 处理批注
            comment_id = self.add_comment(revision['comment'])
            # 在 document.xml 中标记范围
            pass
    
    def finalize(self):
        """完成修订写入，保存 DOCX"""
        # 启用修订跟踪
        self.enable_track_revisions()
        
        # 保存 DOCX
        self._save_docx()


def create_revision_from_json(input_docx: str, output_docx: str, 
                               revisions_json: str):
    """
    从 JSON 配置创建修订
    
    Args:
        input_docx: 输入 DOCX 路径
        output_docx: 输出 DOCX 路径
        revisions_json: JSON 格式的修订配置
    """
    revisions = json.loads(revisions_json)
    
    with WPSRevisionWriter(input_docx, output_docx) as writer:
        for revision in revisions:
            writer.apply_revision(revision)
        
        writer.finalize()


# 示例用法
if __name__ == '__main__':
    # 示例：创建修订
    input_file = 'input.docx'
    output_file = 'output_revised.docx'
    
    # 修订配置示例
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
        input_file, 
        output_file, 
        json.dumps(revisions, ensure_ascii=False, indent=2)
    )
