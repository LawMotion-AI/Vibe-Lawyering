"""
XML 修订痕迹写入功能测试脚本

用于验证 Python 路径的修订、批注、关系文件与 OOXML 结构。
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from typing import Dict, List

from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from internal_write_revisions_xml import WPSRevisionWriter, create_revision_from_json

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PR_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
NAMESPACES = {'w': W_NS, 'pr': PR_NS, 'ct': CT_NS}


def create_test_docx(output_path: str):
    temp_dir = tempfile.mkdtemp()
    try:
        word_dir = os.path.join(temp_dir, 'word')
        rels_dir = os.path.join(temp_dir, '_rels')
        word_rels_dir = os.path.join(word_dir, '_rels')
        os.makedirs(word_dir)
        os.makedirs(rels_dir)
        os.makedirs(word_rels_dir)

        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>'''

        document_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
            xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
  <w:body>
    <w:p>
      <w:r>
        <w:t>这是第一段文本内容</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>这是第二段文本内容，需要修改</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>这是第三段文本内容</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''

        settings_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:compat/>
</w:settings>'''

        root_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

        document_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
</Relationships>'''

        with open(os.path.join(temp_dir, '[Content_Types].xml'), 'w', encoding='utf-8') as handle:
            handle.write(content_types)
        with open(os.path.join(word_dir, 'document.xml'), 'w', encoding='utf-8') as handle:
            handle.write(document_xml)
        with open(os.path.join(word_dir, 'settings.xml'), 'w', encoding='utf-8') as handle:
            handle.write(settings_xml)
        with open(os.path.join(rels_dir, '.rels'), 'w', encoding='utf-8') as handle:
            handle.write(root_rels_xml)
        with open(os.path.join(word_rels_dir, 'document.xml.rels'), 'w', encoding='utf-8') as handle:
            handle.write(document_rels_xml)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(temp_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    archive_name = os.path.relpath(file_path, temp_dir).replace(os.sep, '/')
                    archive.write(file_path, archive_name)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def extract_docx(docx_path: str) -> str:
    extract_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(docx_path, 'r') as archive:
        archive.extractall(extract_dir)
    return extract_dir


def read_xml(xml_path: str) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.parse(xml_path, parser)


def node_text(node: etree._Element) -> str:
    parts: List[str] = []
    for child in node.xpath('.//w:t | .//w:delText | .//w:tab | .//w:br', namespaces=NAMESPACES):
        if child.tag in {f'{{{W_NS}}}t', f'{{{W_NS}}}delText'}:
            parts.append(child.text or '')
        elif child.tag == f'{{{W_NS}}}tab':
            parts.append('\t')
        else:
            parts.append('\n')
    return ''.join(parts)


def visible_node_text(node: etree._Element) -> str:
    parts: List[str] = []
    for child in node.xpath('.//w:t | .//w:tab | .//w:br', namespaces=NAMESPACES):
        if child.tag == f'{{{W_NS}}}t':
            parts.append(child.text or '')
        elif child.tag == f'{{{W_NS}}}tab':
            parts.append('\t')
        else:
            parts.append('\n')
    return ''.join(parts)


def collect_docx_summary(docx_path: str) -> Dict[str, object]:
    extract_dir = extract_docx(docx_path)
    try:
        document_tree = read_xml(os.path.join(extract_dir, 'word', 'document.xml'))
        settings_tree = read_xml(os.path.join(extract_dir, 'word', 'settings.xml'))
        comments_path = os.path.join(extract_dir, 'word', 'comments.xml')
        comments_tree = read_xml(comments_path) if os.path.exists(comments_path) else None
        rels_tree = read_xml(os.path.join(extract_dir, 'word', '_rels', 'document.xml.rels'))
        types_tree = read_xml(os.path.join(extract_dir, '[Content_Types].xml'))

        summary = {
            'del_count': len(document_tree.xpath('//w:del', namespaces=NAMESPACES)),
            'ins_count': len(document_tree.xpath('//w:ins', namespaces=NAMESPACES)),
            'comment_range_start_count': len(document_tree.xpath('//w:commentRangeStart', namespaces=NAMESPACES)),
            'comment_range_end_count': len(document_tree.xpath('//w:commentRangeEnd', namespaces=NAMESPACES)),
            'comment_reference_count': len(document_tree.xpath('//w:commentReference', namespaces=NAMESPACES)),
            'track_revisions': len(settings_tree.xpath('/w:settings/w:trackRevisions', namespaces=NAMESPACES)) == 1,
            'show_revisions': len(settings_tree.xpath('/w:settings/w:showRevisions', namespaces=NAMESPACES)) == 1,
            'has_comments_rel': len(rels_tree.xpath(
                "/pr:Relationships/pr:Relationship[@Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments' and @Target='comments.xml']",
                namespaces=NAMESPACES
            )) == 1,
            'has_settings_rel': len(rels_tree.xpath(
                "/pr:Relationships/pr:Relationship[@Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings' and @Target='settings.xml']",
                namespaces=NAMESPACES
            )) >= 1,
            'has_comments_override': len(types_tree.xpath(
                "/ct:Types/ct:Override[@PartName='/word/comments.xml']",
                namespaces=NAMESPACES
            )) == 1,
            'has_settings_override': len(types_tree.xpath(
                "/ct:Types/ct:Override[@PartName='/word/settings.xml']",
                namespaces=NAMESPACES
            )) == 1,
            'revision_ids': sorted([
                int(node.get(f'{{{W_NS}}}id'))
                for node in document_tree.xpath('//w:del | //w:ins', namespaces=NAMESPACES)
            ]),
            'comment_ids': sorted([
                int(node.get(f'{{{W_NS}}}id'))
                for node in (comments_tree.xpath('//w:comment', namespaces=NAMESPACES) if comments_tree is not None else [])
            ]),
            'comment_texts': [
                '\n'.join(node_text(paragraph) for paragraph in comment.xpath('./w:p', namespaces=NAMESPACES))
                for comment in (comments_tree.xpath('/w:comments/w:comment', namespaces=NAMESPACES) if comments_tree is not None else [])
            ],
            'paragraph_texts': [
                node_text(paragraph)
                for paragraph in document_tree.xpath('//w:body/w:p', namespaces=NAMESPACES)
            ],
            'visible_paragraph_texts': [
                visible_node_text(paragraph)
                for paragraph in document_tree.xpath('//w:body/w:p', namespaces=NAMESPACES)
            ],
            'comment_font_locked': comments_tree is not None and len(comments_tree.xpath(
                "//w:comment//w:rPr/w:rFonts[@w:eastAsia='SimSun' and @w:ascii='SimSun' and @w:hAnsi='SimSun' and @w:cs='SimSun']",
                namespaces=NAMESPACES
            )) >= 1,
        }
        return summary
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def test_basic_markup_generation() -> bool:
    print('\n' + '=' * 60)
    print('测试 1：基本标记生成')
    print('=' * 60)
    input_file = os.path.join(tempfile.gettempdir(), 'test_basic_input.docx')
    output_file = os.path.join(tempfile.gettempdir(), 'test_basic_output.docx')
    try:
        create_test_docx(input_file)
        with WPSRevisionWriter(input_file, output_file) as writer:
            del_xml = writer.add_deletion('测试删除')
            ins_xml = writer.add_insertion('测试插入')
            comment_id = writer.add_comment({'问题': '测试问题', '风险': '测试风险'})
            writer.finalize()

        del_node = etree.fromstring(del_xml.encode('utf-8'))
        ins_node = etree.fromstring(ins_xml.encode('utf-8'))
        assert etree.QName(del_node).localname == 'del'
        assert del_node.get(f'{{{W_NS}}}id') == '0'
        assert etree.QName(ins_node).localname == 'ins'
        assert ins_node.get(f'{{{W_NS}}}id') == '1'
        assert comment_id == 0

        summary = collect_docx_summary(output_file)
        assert summary['track_revisions'] is True
        assert summary['show_revisions'] is True
        assert summary['has_comments_rel'] is True
        assert summary['has_comments_override'] is True
        assert summary['comment_font_locked'] is True
        print('✓ 基本标记、关系文件与字体锁定正常')
        return True
    except Exception as exc:
        print(f'✗ 基本标记生成失败：{exc}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        for path in (input_file, output_file):
            if os.path.exists(path):
                os.remove(path)


def test_apply_revision_with_anchor_and_comment() -> bool:
    print('\n' + '=' * 60)
    print('测试 2：anchor_text + revision_comment')
    print('=' * 60)
    input_file = os.path.join(tempfile.gettempdir(), 'test_anchor_input.docx')
    output_file = os.path.join(tempfile.gettempdir(), 'test_anchor_output.docx')
    try:
        create_test_docx(input_file)
        payload = {
            'author': '法务审核AI',
            'date': '2026-03-19T10:00:00Z',
            'operations': [
                {
                    'mode': 'revision_comment',
                    'anchor_text': '这是第二段文本内容，需要修改',
                    'replacement_text': '这是第二段文本内容，已经修改完成',
                    'match_type': 'exact',
                    'occurrence': 1,
                    'comment': {
                        '问题': '原文表述过于口语化',
                        '风险': '正式合同文本不够严谨',
                        '修改建议': '改为完成态表述',
                        '建议条款': '这是第二段文本内容，已经修改完成'
                    }
                },
                {
                    'mode': 'comment',
                    'anchor_text': '这是第三段文本内容',
                    'comment': {
                        '问题': '第三段缺少责任承接',
                        '风险': '上下文衔接不足',
                        '修改建议': '补强关联条款'
                    }
                }
            ]
        }
        create_revision_from_json(input_file, output_file, json.dumps(payload, ensure_ascii=False))
        summary = collect_docx_summary(output_file)

        assert summary['del_count'] >= 1
        assert summary['ins_count'] >= 1
        assert summary['comment_range_start_count'] == 2
        assert summary['comment_range_end_count'] == 2
        assert summary['comment_reference_count'] == 2
        assert summary['has_comments_rel'] is True
        assert summary['has_settings_rel'] is True
        assert summary['has_comments_override'] is True
        assert summary['has_settings_override'] is True
        assert summary['comment_font_locked'] is True
        assert len(summary['comment_texts']) == 2
        assert summary['comment_ids'] == [0, 1]
        assert summary['ins_count'] == 1
        assert summary['visible_paragraph_texts'][1] == '这是第二段文本内容，已经修改完成'
        assert summary['comment_texts'][0] == (
            '问题：原文表述过于口语化\n'
            '风险：正式合同文本不够严谨\n'
            '修改建议：改为完成态表述\n'
            '建议条款：这是第二段文本内容，已经修改完成'
        )
        assert '完成态 表述' not in summary['comment_texts'][0]
        print('✓ anchor 定位、最小 diff、批注范围与 comments.xml 全部生效')
        return True
    except Exception as exc:
        print(f'✗ anchor_text 路径失败：{exc}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        for path in (input_file, output_file):
            if os.path.exists(path):
                os.remove(path)


def test_apply_revision_with_location() -> bool:
    print('\n' + '=' * 60)
    print('测试 3：location 段落定位')
    print('=' * 60)
    input_file = os.path.join(tempfile.gettempdir(), 'test_location_input.docx')
    output_file = os.path.join(tempfile.gettempdir(), 'test_location_output.docx')
    try:
        create_test_docx(input_file)
        payload = {
            'author': '定位测试员',
            'operations': [
                {
                    'mode': 'revision',
                    'location': {'paragraph': 1},
                    'replacement_text': '这是第一段文本内容（已定位修改）'
                },
                {
                    'mode': 'comment',
                    'location': {'paragraph': 3},
                    'comment': '问题：第三段需要后续人工确认'
                }
            ]
        }
        create_revision_from_json(input_file, output_file, json.dumps(payload, ensure_ascii=False))
        summary = collect_docx_summary(output_file)

        assert summary['ins_count'] >= 1
        assert summary['comment_range_start_count'] == 1
        assert any('人工确认' in text for text in summary['comment_texts'])
        assert summary['revision_ids'] == sorted(summary['revision_ids'])
        assert summary['visible_paragraph_texts'][0] == '这是第一段文本内容（已定位修改）'
        print('✓ location 定位与修订 ID 排序正常')
        return True
    except Exception as exc:
        print(f'✗ location 路径失败：{exc}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        for path in (input_file, output_file):
            if os.path.exists(path):
                os.remove(path)


def main() -> int:
    print('\n' + '=' * 60)
    print('Python XML 修订路径测试')
    print('=' * 60)
    tests = [
        ('基本标记生成', test_basic_markup_generation),
        ('anchor_text + revision_comment', test_apply_revision_with_anchor_and_comment),
        ('location 段落定位', test_apply_revision_with_location),
    ]
    results = []
    for name, test_func in tests:
        try:
            results.append((name, test_func()))
        except Exception as exc:
            print(f'✗ {name} 测试异常：{exc}')
            results.append((name, False))

    print('\n' + '=' * 60)
    print('测试结果汇总')
    print('=' * 60)
    for name, passed in results:
        print(f'{"✓ 通过" if passed else "✗ 失败"} - {name}')
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f'\n总计：{passed_count}/{total_count} 通过')
    return 0 if passed_count == total_count else 1


if __name__ == '__main__':
    sys.exit(main())
