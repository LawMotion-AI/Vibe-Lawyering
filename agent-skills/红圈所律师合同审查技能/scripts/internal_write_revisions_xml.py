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

import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree


class WPSRevisionWriter:
    """WPS 兼容的修订痕迹写入器"""
    
    # Word ML 命名空间
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
        'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    PACKAGE_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
    CONTENT_TYPES_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
    XML_NS = 'http://www.w3.org/XML/1998/namespace'
    COMMENT_KEYS = ('问题', '风险', '修改建议', '建议条款', '修改依据')
    DIFF_TOKEN_PATTERN = re.compile(
        r"[0-9]+(?:[.,][0-9]+)*|[A-Za-z]+(?:[-_'][A-Za-z]+)*|[\u4e00-\u9fff]|[^\S\r\n]+|\r\n|\n|\r|.",
        re.UNICODE
    )
    
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
        self.content_types_xml_path = os.path.join(self.temp_dir, '[Content_Types].xml')
        self.document_rels_path = os.path.join(self.temp_dir, 'word', '_rels', 'document.xml.rels')
        self.comment_font = 'SimSun'
        
        # 修订计数器
        self.revision_id_counter = 0
        self.comment_id_counter = 0
        
        # 修订作者信息
        self.author = "合同审核人"
        self.date_format = "%Y-%m-%dT%H:%M:%SZ"
        
    def __enter__(self):
        """上下文管理器入口"""
        self._extract_docx()
        self._initialize_counters()
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

    def _load_content_types_xml(self) -> etree._ElementTree:
        if not os.path.exists(self.content_types_xml_path):
            root = etree.Element(
                f'{{{self.CONTENT_TYPES_NS}}}Types',
                nsmap={None: self.CONTENT_TYPES_NS}
            )
            tree = etree.ElementTree(root)
            self._save_content_types_xml(tree)
            return tree
        parser = etree.XMLParser(remove_blank_text=False)
        return etree.parse(self.content_types_xml_path, parser)

    def _save_content_types_xml(self, tree: etree._ElementTree):
        tree.write(
            self.content_types_xml_path,
            xml_declaration=True,
            encoding='UTF-8',
            standalone='yes'
        )

    def _load_document_rels_xml(self) -> etree._ElementTree:
        if not os.path.exists(self.document_rels_path):
            rels_dir = os.path.dirname(self.document_rels_path)
            if rels_dir and not os.path.exists(rels_dir):
                os.makedirs(rels_dir)
            root = etree.Element(
                f'{{{self.PACKAGE_REL_NS}}}Relationships',
                nsmap={None: self.PACKAGE_REL_NS}
            )
            tree = etree.ElementTree(root)
            self._save_document_rels_xml(tree)
            return tree
        parser = etree.XMLParser(remove_blank_text=False)
        return etree.parse(self.document_rels_path, parser)

    def _save_document_rels_xml(self, tree: etree._ElementTree):
        tree.write(
            self.document_rels_path,
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

    def _initialize_counters(self):
        document_tree = self._load_document_xml()
        revision_ids = []
        for node in document_tree.xpath('//w:del | //w:ins', namespaces=self.NAMESPACES):
            revision_id = node.get(f'{{{self.NAMESPACES["w"]}}}id')
            if revision_id and revision_id.isdigit():
                revision_ids.append(int(revision_id))
        self.revision_id_counter = max(revision_ids, default=-1) + 1

        if os.path.exists(self.comments_xml_path):
            comments_tree = self._load_comments_xml()
            comment_ids = []
            for node in comments_tree.xpath('//w:comment', namespaces=self.NAMESPACES):
                comment_id = node.get(f'{{{self.NAMESPACES["w"]}}}id')
                if comment_id and comment_id.isdigit():
                    comment_ids.append(int(comment_id))
            self.comment_id_counter = max(comment_ids, default=-1) + 1

    def _ensure_relationship(self, rel_type: str, target: str):
        rels_tree = self._load_document_rels_xml()
        rels_root = rels_tree.getroot()
        existing = rels_root.xpath(
            './pr:Relationship[@Type=$rel_type and @Target=$target]',
            namespaces={'pr': self.PACKAGE_REL_NS},
            rel_type=rel_type,
            target=target
        )
        if not existing:
            relationship_ids = []
            for node in rels_root.xpath('./pr:Relationship', namespaces={'pr': self.PACKAGE_REL_NS}):
                rel_id = node.get('Id', '')
                if rel_id.startswith('rId') and rel_id[3:].isdigit():
                    relationship_ids.append(int(rel_id[3:]))
            new_rel = etree.Element(f'{{{self.PACKAGE_REL_NS}}}Relationship')
            new_rel.set('Id', f'rId{max(relationship_ids, default=0) + 1}')
            new_rel.set('Type', rel_type)
            new_rel.set('Target', target)
            rels_root.append(new_rel)
            self._save_document_rels_xml(rels_tree)

    def _ensure_content_type_override(self, part_name: str, content_type: str):
        content_types_tree = self._load_content_types_xml()
        content_types_root = content_types_tree.getroot()
        override = content_types_root.xpath(
            './ct:Override[@PartName=$part_name]',
            namespaces={'ct': self.CONTENT_TYPES_NS},
            part_name=part_name
        )
        if override:
            override[0].set('ContentType', content_type)
        else:
            node = etree.Element(f'{{{self.CONTENT_TYPES_NS}}}Override')
            node.set('PartName', part_name)
            node.set('ContentType', content_type)
            content_types_root.append(node)
        self._save_content_types_xml(content_types_tree)

    def _ensure_comments_part(self):
        self._load_comments_xml()
        self._ensure_relationship(
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments',
            'comments.xml'
        )
        self._ensure_content_type_override(
            '/word/comments.xml',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'
        )

    def _ensure_settings_part(self):
        self._load_settings_xml()
        self._ensure_relationship(
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings',
            'settings.xml'
        )
        self._ensure_content_type_override(
            '/word/settings.xml',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml'
        )
    
    def _update_document_rels(self):
        """更新 document.xml.rels 文件，添加对 comments.xml 的引用"""
        self._ensure_comments_part()
    
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

    def _clone_run_properties(self, paragraph_elem: etree._Element) -> Optional[etree._Element]:
        for run_elem in paragraph_elem.findall('./w:r', namespaces=self.NAMESPACES):
            run_props = run_elem.find('./w:rPr', namespaces=self.NAMESPACES)
            if run_props is not None:
                return etree.fromstring(etree.tostring(run_props))
        return None

    def _append_text_nodes(self, run_elem: etree._Element, text: str, deleted: bool = False):
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        xml_ns = '{http://www.w3.org/XML/1998/namespace}'
        tag_name = f'{w_ns}delText' if deleted else f'{w_ns}t'
        buffer: List[str] = []

        def flush_buffer():
            if not buffer:
                return
            node = etree.Element(tag_name)
            value = ''.join(buffer)
            if value.startswith(' ') or value.endswith(' ') or '  ' in value:
                node.set(f'{xml_ns}space', 'preserve')
            node.text = value
            run_elem.append(node)
            buffer.clear()

        for char in text:
            if char == '\n':
                flush_buffer()
                run_elem.append(etree.Element(f'{w_ns}br'))
            elif char == '\t':
                flush_buffer()
                run_elem.append(etree.Element(f'{w_ns}tab'))
            else:
                buffer.append(char)

        flush_buffer()
        if len(run_elem) == 0:
            node = etree.Element(tag_name)
            node.text = ''
            run_elem.append(node)

    def _append_run(
        self,
        parent_elem: etree._Element,
        text: str,
        run_props: Optional[etree._Element] = None,
        deleted: bool = False
    ) -> etree._Element:
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        run_elem = etree.Element(f'{w_ns}r')
        if run_props is not None:
            run_elem.append(etree.fromstring(etree.tostring(run_props)))
        self._append_text_nodes(run_elem, text, deleted=deleted)
        parent_elem.append(run_elem)
        return run_elem

    def _paragraph_text(self, paragraph_elem: etree._Element) -> str:
        parts: List[str] = []
        xpath = './/w:t | .//w:delText | .//w:instrText | .//w:tab | .//w:br | .//w:cr'
        for node in paragraph_elem.xpath(xpath, namespaces=self.NAMESPACES):
            if node.tag in {
                f'{{{self.NAMESPACES["w"]}}}t',
                f'{{{self.NAMESPACES["w"]}}}delText',
                f'{{{self.NAMESPACES["w"]}}}instrText'
            }:
                parts.append(node.text or '')
            elif node.tag == f'{{{self.NAMESPACES["w"]}}}tab':
                parts.append('\t')
            else:
                parts.append('\n')
        return ''.join(parts)

    def _normalize_text(self, text: Optional[str]) -> str:
        return re.sub(r'\s+', ' ', text or '').strip()

    def _snapshot_paragraph(self, paragraph_elem: etree._Element) -> Tuple[Optional[etree._Element], List[etree._Element]]:
        ppr_clone = None
        content_clones: List[etree._Element] = []
        for child in list(paragraph_elem):
            cloned = etree.fromstring(etree.tostring(child))
            if child.tag == f'{{{self.NAMESPACES["w"]}}}pPr':
                ppr_clone = cloned
            else:
                content_clones.append(cloned)
            paragraph_elem.remove(child)
        return ppr_clone, content_clones

    def _restore_snapshot_content(
        self,
        paragraph_elem: etree._Element,
        content_nodes: List[etree._Element],
        fallback_text: str,
        run_props: Optional[etree._Element]
    ):
        if content_nodes:
            for node in content_nodes:
                paragraph_elem.append(node)
            return
        self._append_run(paragraph_elem, fallback_text, run_props=run_props, deleted=False)

    def _create_comment_marker(self, local_name: str, comment_id: int) -> etree._Element:
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        node = etree.Element(f'{w_ns}{local_name}')
        node.set(f'{w_ns}id', str(comment_id))
        return node

    def _create_comment_reference_run(self, comment_id: int) -> etree._Element:
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        run_elem = etree.Element(f'{w_ns}r')
        run_props = etree.Element(f'{w_ns}rPr')
        run_style = etree.Element(f'{w_ns}rStyle')
        run_style.set(f'{w_ns}val', 'CommentReference')
        run_props.append(run_style)
        run_elem.append(run_props)
        reference = etree.Element(f'{w_ns}commentReference')
        reference.set(f'{w_ns}id', str(comment_id))
        run_elem.append(reference)
        return run_elem

    def _tokenize_diff_text(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        return self.DIFF_TOKEN_PATTERN.findall(text)

    def _merge_diff_segments(self, segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        merged: List[Tuple[str, str]] = []
        for kind, text in segments:
            if not text:
                continue
            if merged and merged[-1][0] == kind:
                merged[-1] = (kind, merged[-1][1] + text)
            else:
                merged.append((kind, text))
        return merged

    def _is_mergeable_equal_segment(self, text: str) -> bool:
        if not text or re.search(r'\s', text):
            return False
        if re.fullmatch(r'[\u4e00-\u9fff]{1,2}', text):
            return True
        if re.fullmatch(r'[A-Za-z0-9]{1,4}', text):
            return True
        return False

    def _collapse_diff_window(self, window_segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        if not window_segments:
            return []
        change_count = sum(1 for kind, _ in window_segments if kind != 'equal')
        has_equal = any(kind == 'equal' for kind, _ in window_segments)
        if change_count <= 1 and not has_equal:
            return window_segments
        old_text = ''.join(text for kind, text in window_segments if kind in {'equal', 'del'})
        new_text = ''.join(text for kind, text in window_segments if kind in {'equal', 'ins'})
        collapsed: List[Tuple[str, str]] = []
        if old_text:
            collapsed.append(('del', old_text))
        if new_text:
            collapsed.append(('ins', new_text))
        return collapsed

    def _coalesce_change_windows(self, segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        if not segments:
            return []
        coalesced: List[Tuple[str, str]] = []
        window: List[Tuple[str, str]] = []
        for index, segment in enumerate(segments):
            kind, text = segment
            prev_kind = segments[index - 1][0] if index > 0 else None
            next_kind = segments[index + 1][0] if index + 1 < len(segments) else None
            is_connector = (
                kind == 'equal' and
                prev_kind is not None and
                next_kind is not None and
                prev_kind != 'equal' and
                next_kind != 'equal' and
                self._is_mergeable_equal_segment(text)
            )
            if kind != 'equal' or is_connector:
                window.append(segment)
                continue
            if window:
                coalesced.extend(self._collapse_diff_window(window))
                window = []
            coalesced.append(segment)
        if window:
            coalesced.extend(self._collapse_diff_window(window))
        return self._merge_diff_segments(coalesced)

    def _slice_token_text(self, tokens: List[str], start: int, count: int) -> str:
        if count <= 0:
            return ''
        return ''.join(tokens[start:start + count])

    def _common_prefix_count(self, left_tokens: List[str], right_tokens: List[str]) -> int:
        count = 0
        max_count = min(len(left_tokens), len(right_tokens))
        while count < max_count and left_tokens[count] == right_tokens[count]:
            count += 1
        return count

    def _common_suffix_count(
        self,
        left_tokens: List[str],
        right_tokens: List[str],
        prefix_count: int
    ) -> int:
        left_remaining = len(left_tokens) - prefix_count
        right_remaining = len(right_tokens) - prefix_count
        max_count = min(left_remaining, right_remaining)
        count = 0
        while (
            count < max_count and
            left_tokens[len(left_tokens) - 1 - count] == right_tokens[len(right_tokens) - 1 - count]
        ):
            count += 1
        return count

    def _get_fallback_diff_segments(
        self,
        old_tokens: List[str],
        new_tokens: List[str]
    ) -> List[Tuple[str, str]]:
        segments: List[Tuple[str, str]] = []
        prefix_count = self._common_prefix_count(old_tokens, new_tokens)
        suffix_count = self._common_suffix_count(old_tokens, new_tokens, prefix_count)
        old_middle_count = len(old_tokens) - prefix_count - suffix_count
        new_middle_count = len(new_tokens) - prefix_count - suffix_count
        if prefix_count > 0:
            segments.append(('equal', self._slice_token_text(old_tokens, 0, prefix_count)))
        if old_middle_count > 0:
            segments.append(('del', self._slice_token_text(old_tokens, prefix_count, old_middle_count)))
        if new_middle_count > 0:
            segments.append(('ins', self._slice_token_text(new_tokens, prefix_count, new_middle_count)))
        if suffix_count > 0:
            segments.append(('equal', self._slice_token_text(old_tokens, len(old_tokens) - suffix_count, suffix_count)))
        return self._coalesce_change_windows(self._merge_diff_segments(segments))

    def _get_mid_diff_segments(
        self,
        old_tokens: List[str],
        new_tokens: List[str]
    ) -> List[Tuple[str, str]]:
        if not old_tokens and not new_tokens:
            return []
        if not old_tokens:
            return [('ins', ''.join(new_tokens))]
        if not new_tokens:
            return [('del', ''.join(old_tokens))]

        cell_limit = 4_000_000
        cells = (len(old_tokens) + 1) * (len(new_tokens) + 1)
        if cells > cell_limit:
            return self._get_fallback_diff_segments(old_tokens, new_tokens)

        dp = [[0] * (len(new_tokens) + 1) for _ in range(len(old_tokens) + 1)]
        for i in range(len(old_tokens) + 1):
            dp[i][0] = i
        for j in range(len(new_tokens) + 1):
            dp[0][j] = j

        for i in range(1, len(old_tokens) + 1):
            for j in range(1, len(new_tokens) + 1):
                if old_tokens[i - 1] == new_tokens[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    delete_cost = dp[i - 1][j] + 1
                    insert_cost = dp[i][j - 1] + 1
                    replace_cost = dp[i - 1][j - 1] + 2
                    dp[i][j] = min(replace_cost, delete_cost, insert_cost)

        units: List[Tuple[str, str]] = []
        i = len(old_tokens)
        j = len(new_tokens)
        while i > 0 or j > 0:
            if (
                i > 0 and j > 0 and
                old_tokens[i - 1] == new_tokens[j - 1] and
                dp[i][j] == dp[i - 1][j - 1]
            ):
                units.append(('equal', old_tokens[i - 1]))
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                units.append(('del', old_tokens[i - 1]))
                i -= 1
            elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
                units.append(('ins', new_tokens[j - 1]))
                j -= 1
            else:
                if j > 0:
                    units.append(('ins', new_tokens[j - 1]))
                    j -= 1
                if i > 0:
                    units.append(('del', old_tokens[i - 1]))
                    i -= 1

        units.reverse()
        return self._merge_diff_segments(units)

    def _get_minimal_diff_segments(self, old_text: Optional[str], new_text: Optional[str]) -> List[Tuple[str, str]]:
        old_tokens = self._tokenize_diff_text(old_text or '')
        new_tokens = self._tokenize_diff_text(new_text or '')
        segments: List[Tuple[str, str]] = []
        prefix_count = self._common_prefix_count(old_tokens, new_tokens)
        suffix_count = self._common_suffix_count(old_tokens, new_tokens, prefix_count)
        old_middle_count = len(old_tokens) - prefix_count - suffix_count
        new_middle_count = len(new_tokens) - prefix_count - suffix_count

        if prefix_count > 0:
            segments.append(('equal', self._slice_token_text(old_tokens, 0, prefix_count)))
        if old_middle_count > 0 or new_middle_count > 0:
            old_middle = old_tokens[prefix_count:prefix_count + old_middle_count] if old_middle_count > 0 else []
            new_middle = new_tokens[prefix_count:prefix_count + new_middle_count] if new_middle_count > 0 else []
            segments.extend(self._get_mid_diff_segments(old_middle, new_middle))
        if suffix_count > 0:
            segments.append(('equal', self._slice_token_text(old_tokens, len(old_tokens) - suffix_count, suffix_count)))
        return self._coalesce_change_windows(self._merge_diff_segments(segments))

    def _build_revision_element(
        self,
        local_name: str,
        text: str,
        revision_id: int,
        author: str,
        date: str,
        run_props: Optional[etree._Element]
    ) -> etree._Element:
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        node = etree.Element(f'{w_ns}{local_name}')
        node.set(f'{w_ns}author', author)
        node.set(f'{w_ns}date', date)
        node.set(f'{w_ns}id', str(revision_id))
        self._append_run(node, text, run_props=run_props, deleted=(local_name == 'del'))
        return node

    def _write_revision_segments(
        self,
        paragraph_elem: etree._Element,
        segments: List[Tuple[str, str]],
        author: str,
        date: str,
        run_props: Optional[etree._Element]
    ) -> bool:
        changed = False
        for kind, text in segments:
            if not text:
                continue
            if kind == 'equal':
                self._append_run(paragraph_elem, text, run_props=run_props, deleted=False)
            elif kind == 'del':
                paragraph_elem.append(
                    self._build_revision_element(
                        'del',
                        text,
                        self.revision_id_counter,
                        author,
                        date,
                        run_props
                    )
                )
                self.revision_id_counter += 1
                changed = True
            elif kind == 'ins':
                paragraph_elem.append(
                    self._build_revision_element(
                        'ins',
                        text,
                        self.revision_id_counter,
                        author,
                        date,
                        run_props
                    )
                )
                self.revision_id_counter += 1
                changed = True
        return changed

    def _get_paragraphs(self, tree: etree._ElementTree) -> List[etree._Element]:
        return tree.xpath('//w:p', namespaces=self.NAMESPACES)

    def _find_paragraph_by_location(
        self,
        document_tree: etree._ElementTree,
        location: Optional[Dict[str, Any]]
    ) -> Optional[etree._Element]:
        if not location:
            return None
        paragraphs = self._get_paragraphs(document_tree)
        if 'paragraph_index' in location:
            index = int(location['paragraph_index'])
        elif 'paragraph' in location:
            raw_index = int(location['paragraph'])
            if raw_index <= 0:
                index = 0
            elif raw_index < len(paragraphs) and raw_index not in (len(paragraphs),):
                index = raw_index - 1
            else:
                index = raw_index - 1
        else:
            return None
        if index < 0 or index >= len(paragraphs):
            raise ValueError(f'段落索引超出范围: {index}')
        return paragraphs[index]

    def _find_paragraph_by_anchor(
        self,
        document_tree: etree._ElementTree,
        anchor_text: str,
        match_type: str = 'exact',
        occurrence: int = 1
    ) -> etree._Element:
        paragraphs = self._get_paragraphs(document_tree)
        normalized_anchor = self._normalize_text(anchor_text)
        matched: List[etree._Element] = []
        for paragraph in paragraphs:
            normalized_text = self._normalize_text(self._paragraph_text(paragraph))
            if match_type == 'contains':
                if normalized_anchor in normalized_text:
                    matched.append(paragraph)
            else:
                if normalized_text == normalized_anchor:
                    matched.append(paragraph)
        if occurrence <= 0:
            raise ValueError(f'occurrence 必须为正整数: {occurrence}')
        if len(matched) < occurrence:
            raise ValueError(f'未找到第 {occurrence} 个匹配段落: {anchor_text}')
        return matched[occurrence - 1]

    def _format_comment_text(self, comment_value: Any) -> str:
        if isinstance(comment_value, dict):
            lines = [
                f'{key}：{comment_value[key]}'
                for key in self.COMMENT_KEYS
                if key in comment_value and str(comment_value[key]).strip()
            ]
            return '\n'.join(lines) if lines else '问题：未提供批注内容'
        return str(comment_value or '问题：未提供批注内容')

    def _normalize_revision(self, revision: Dict[str, Any]) -> Dict[str, Any]:
        author = str(revision.get('author') or self.author)
        date = str(revision.get('date') or self._get_current_date())

        if 'mode' in revision or 'anchor_text' in revision or 'replacement_text' in revision:
            mode = str(revision.get('mode') or 'revision_comment').lower()
            anchor_text = revision.get('anchor_text')
            location = revision.get('location')
            replacement_text = revision.get('replacement_text')
            comment_text = self._format_comment_text(revision.get('comment'))
            match_type = str(revision.get('match_type') or 'exact').lower()
            occurrence = int(revision.get('occurrence') or 1)
            return {
                'mode': mode,
                'anchor_text': anchor_text,
                'location': location,
                'replacement_text': replacement_text,
                'comment_text': comment_text,
                'match_type': match_type,
                'occurrence': occurrence,
                'author': author,
                'date': date,
                'legacy_type': None,
                'legacy_text': None
            }

        legacy_type = str(revision.get('type') or '').lower()
        if legacy_type not in {'delete', 'insert', 'comment'}:
            raise ValueError(f'不支持的修订类型: {legacy_type}')
        comment_text = self._format_comment_text(revision.get('comment'))
        return {
            'mode': 'comment' if legacy_type == 'comment' else 'revision',
            'anchor_text': revision.get('anchor_text') or revision.get('text'),
            'location': revision.get('location'),
            'replacement_text': revision.get('replacement_text'),
            'comment_text': comment_text,
            'match_type': str(revision.get('match_type') or 'exact').lower(),
            'occurrence': int(revision.get('occurrence') or 1),
            'author': author,
            'date': date,
            'legacy_type': legacy_type,
            'legacy_text': revision.get('text')
        }

    def _resolve_target_paragraph(self, document_tree: etree._ElementTree, normalized_revision: Dict[str, Any]) -> etree._Element:
        paragraph = self._find_paragraph_by_location(document_tree, normalized_revision.get('location'))
        if paragraph is not None:
            return paragraph
        anchor_text = normalized_revision.get('anchor_text')
        if anchor_text:
            return self._find_paragraph_by_anchor(
                document_tree,
                str(anchor_text),
                match_type=str(normalized_revision.get('match_type') or 'exact'),
                occurrence=int(normalized_revision.get('occurrence') or 1)
            )
        raise ValueError('修订缺少段落定位信息：需要 location 或 anchor_text')

    def _resolve_replacement_text(self, normalized_revision: Dict[str, Any], original_text: str) -> Optional[str]:
        if normalized_revision.get('replacement_text') is not None:
            return str(normalized_revision['replacement_text'])
        legacy_type = normalized_revision.get('legacy_type')
        legacy_text = str(normalized_revision.get('legacy_text') or '')
        if legacy_type == 'delete':
            if legacy_text and legacy_text in original_text:
                return original_text.replace(legacy_text, '', 1)
            raise ValueError(f'删除文本未在目标段落中找到: {legacy_text}')
        if legacy_type == 'insert':
            anchor_text = normalized_revision.get('anchor_text')
            if anchor_text and str(anchor_text) in original_text and legacy_text:
                return original_text.replace(str(anchor_text), f'{anchor_text}{legacy_text}', 1)
            if legacy_text:
                return f'{original_text}{legacy_text}'
        return None
    
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
        
        del_id = self.revision_id_counter
        self.revision_id_counter += 1
        
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
        del_elem.set(f'{w_ns}id', str(del_id))
        
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
        
        ins_id = self.revision_id_counter
        self.revision_id_counter += 1
        
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # <w:ins w:author="作者" w:date="时间" w:insId="ID">
        #   <w:r>
        #     <w:t>插入的文本</w:t>
        #   </w:r>
        # </w:ins>
        
        ins_elem = etree.Element(f'{w_ns}ins')
        ins_elem.set(f'{w_ns}author', author)
        ins_elem.set(f'{w_ns}date', date)
        ins_elem.set(f'{w_ns}id', str(ins_id))
        
        run_elem = etree.Element(f'{w_ns}r')
        text_elem = etree.Element(f'{w_ns}t')
        text_elem.text = text
        
        run_elem.append(text_elem)
        ins_elem.append(run_elem)
        
        return etree.tostring(ins_elem, encoding='unicode', xml_declaration=False)
    
    def add_comment(self, comment_text: Any, comment_id: Optional[int] = None,
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
        self._ensure_comments_part()
        
        # 加载 comments.xml
        comments_tree = self._load_comments_xml()
        comments_root = comments_tree.getroot()
        formatted_comment = self._format_comment_text(comment_text)
        comment_lines = formatted_comment.splitlines() or [formatted_comment]
        
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
        
        for line in comment_lines:
            para_elem = etree.Element(f'{w_ns}p')
            run_elem = etree.Element(f'{w_ns}r')
            self._append_comment_run_properties(run_elem)
            self._append_text_nodes(run_elem, line or '', deleted=False)
            para_elem.append(run_elem)
            comment_elem.append(para_elem)
        
        comments_root.append(comment_elem)
        
        # 保存 comments.xml
        self._save_comments_xml(comments_tree)
        
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
        
        paragraph_text = self._paragraph_text(paragraph_elem)
        if text and self._normalize_text(text) not in self._normalize_text(paragraph_text):
            raise ValueError(f'目标段落中未找到批注锚点文本: {text}')
        ppr_clone, content_clones = self._snapshot_paragraph(paragraph_elem)
        if ppr_clone is not None:
            paragraph_elem.append(ppr_clone)
        paragraph_elem.append(self._create_comment_marker('commentRangeStart', comment_id))
        run_props = self._clone_run_properties(paragraph_elem)
        self._restore_snapshot_content(
            paragraph_elem,
            content_clones,
            paragraph_text,
            run_props
        )
        paragraph_elem.append(self._create_comment_marker('commentRangeEnd', comment_id))
        paragraph_elem.append(self._create_comment_reference_run(comment_id))
    
    def enable_track_revisions(self):
        """在 settings.xml 中启用修订跟踪"""
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        self._ensure_settings_part()
        settings_tree = self._load_settings_xml()
        settings_root = settings_tree.getroot()
        
        # 添加或更新 trackRevisions
        track_elem = settings_root.find(f'{w_ns}trackRevisions')
        if track_elem is None:
            track_elem = etree.Element(f'{w_ns}trackRevisions')
            settings_root.append(track_elem)
        track_elem.set(f'{w_ns}val', '1')

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
        normalized_revision = self._normalize_revision(revision)
        document_tree = self._load_document_xml()
        paragraph_elem = self._resolve_target_paragraph(document_tree, normalized_revision)
        original_text = self._paragraph_text(paragraph_elem)
        replacement_text = self._resolve_replacement_text(normalized_revision, original_text)
        run_props = self._clone_run_properties(paragraph_elem)
        ppr_clone, content_clones = self._snapshot_paragraph(paragraph_elem)

        if ppr_clone is not None:
            paragraph_elem.append(ppr_clone)

        comment_id = None
        if normalized_revision['mode'] in {'comment', 'revision_comment'}:
            comment_id = self.add_comment(
                normalized_revision['comment_text'],
                author=normalized_revision['author'],
                date=normalized_revision['date']
            )
            paragraph_elem.append(self._create_comment_marker('commentRangeStart', comment_id))

        if normalized_revision['mode'] == 'comment':
            self._restore_snapshot_content(paragraph_elem, content_clones, original_text, run_props)
        elif normalized_revision['mode'] in {'revision', 'revision_comment'}:
            if replacement_text is None:
                raise ValueError('修订缺少 replacement_text')
            segments = self._get_minimal_diff_segments(original_text, replacement_text)
            changed = self._write_revision_segments(
                paragraph_elem,
                segments,
                normalized_revision['author'],
                normalized_revision['date'],
                run_props
            )
            if not changed:
                self._append_run(paragraph_elem, original_text, run_props=run_props, deleted=False)
        else:
            raise ValueError(f'不支持的修订模式: {normalized_revision["mode"]}')

        if comment_id is not None:
            paragraph_elem.append(self._create_comment_marker('commentRangeEnd', comment_id))
            paragraph_elem.append(self._create_comment_reference_run(comment_id))

        self._save_document_xml(document_tree)
    
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
    payload = json.loads(revisions_json)
    if isinstance(payload, dict):
        revisions = payload.get('operations') or payload.get('revisions') or []
        author = payload.get('author')
        date = payload.get('date')
    else:
        revisions = payload
        author = None
        date = None
    
    with WPSRevisionWriter(input_docx, output_docx) as writer:
        if author:
            writer.author = str(author)
        for revision in revisions:
            if author or date:
                revision = dict(revision)
                if author and 'author' not in revision:
                    revision['author'] = author
                if date and 'date' not in revision:
                    revision['date'] = date
            writer.apply_revision(revision)
        
        writer.finalize()


# 示例用法
if __name__ == '__main__':
    # 示例：创建修订
    input_file = 'input.docx'
    output_file = 'output_revised.docx'
    
    # 修订配置示例
    revisions = {
        'author': '合同审核AI',
        'operations': [
            {
                'mode': 'revision_comment',
                'anchor_text': '原条款内容',
                'replacement_text': '修订后条款内容',
                'match_type': 'exact',
                'occurrence': 1,
                'comment': {
                    '问题': '原条款表述不完整',
                    '风险': '可能导致责任边界不清',
                    '修改建议': '改为更完整的责任承担条款',
                    '建议条款': '修订后条款内容'
                }
            }
        ]
    }
    
    create_revision_from_json(
        input_file, 
        output_file, 
        json.dumps(revisions, ensure_ascii=False, indent=2)
    )
