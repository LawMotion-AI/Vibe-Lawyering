"""
XML 修订痕迹写入功能测试脚本

用于验证 WPSRevisionWriter 的各项功能是否正常工作
"""

import os
import sys
import tempfile
import zipfile
from lxml import etree

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from write_revisions_xml import WPSRevisionWriter


def create_test_docx(output_path):
    """
    创建一个简单的测试用 DOCX 文件
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    word_dir = os.path.join(temp_dir, 'word')
    os.makedirs(word_dir)
    
    # 创建 [Content_Types].xml
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>'''
    
    with open(os.path.join(temp_dir, '[Content_Types].xml'), 'w', encoding='utf-8') as f:
        f.write(content_types)
    
    # 创建 word/document.xml
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
    
    with open(os.path.join(word_dir, 'document.xml'), 'w', encoding='utf-8') as f:
        f.write(document_xml)
    
    # 创建 word/settings.xml
    settings_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:compat/>
</w:settings>'''
    
    with open(os.path.join(word_dir, 'settings.xml'), 'w', encoding='utf-8') as f:
        f.write(settings_xml)
    
    # 创建 _rels/.rels
    rels_dir = os.path.join(temp_dir, '_rels')
    os.makedirs(rels_dir)
    rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    
    with open(os.path.join(rels_dir, '.rels'), 'w', encoding='utf-8') as f:
        f.write(rels_xml)
    
    # 打包成 ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                arcname = arcname.replace(os.sep, '/')
                zip_ref.write(file_path, arcname)
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir)
    
    print(f"✓ 创建测试文件：{output_path}")


def test_basic_revision():
    """
    测试基本修订功能
    """
    print("\n" + "=" * 60)
    print("测试 1：基本修订功能")
    print("=" * 60)
    
    temp_dir = tempfile.gettempdir()
    input_file = os.path.join(temp_dir, 'test_input.docx')
    output_file = os.path.join(temp_dir, 'test_output.docx')
    
    try:
        # 创建测试文件
        create_test_docx(input_file)
        
        # 测试修订
        with WPSRevisionWriter(input_file, output_file) as writer:
            # 测试删除标记
            print("\n1. 测试删除标记...")
            del_xml = writer.add_deletion("测试删除")
            assert 'w:del' in del_xml
            assert 'w:author' in del_xml
            assert 'w:date' in del_xml
            assert 'w:delId' in del_xml
            print("   ✓ 删除标记格式正确")
            
            # 测试插入标记
            print("2. 测试插入标记...")
            ins_xml = writer.add_insertion("测试插入")
            assert 'w:ins' in ins_xml
            assert 'w:author' in ins_xml
            assert 'w:date' in ins_xml
            assert 'w:insId' in ins_xml
            print("   ✓ 插入标记格式正确")
            
            # 测试批注
            print("3. 测试批注功能...")
            comment_id = writer.add_comment("测试批注内容")
            assert isinstance(comment_id, int)
            assert comment_id > 0
            print(f"   ✓ 批注创建成功，ID: {comment_id}")
            
            # 完成修订
            print("4. 完成修订...")
            writer.finalize()
        
        # 验证输出文件
        print("5. 验证输出文件...")
        assert os.path.exists(output_file)
        print("   ✓ 输出文件存在")
        
        # 检查 ZIP 结构
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            assert 'word/document.xml' in file_list
            assert 'word/settings.xml' in file_list
            print("   ✓ ZIP 结构正确")
            
            # 检查 settings.xml
            settings_content = zip_ref.read('word/settings.xml').decode('utf-8')
            assert 'trackRevisions' in settings_content
            assert 'showRevisions' in settings_content
            print("   ✓ settings.xml 已启用修订跟踪")
            
            # 检查 comments.xml
            if 'word/comments.xml' in file_list:
                comments_content = zip_ref.read('word/comments.xml').decode('utf-8')
                assert 'w:comment' in comments_content
                print("   ✓ comments.xml 存在且包含批注")
        
        print("\n✓ 测试 1 通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试 1 失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        for f in [input_file, output_file]:
            if os.path.exists(f):
                os.remove(f)


def test_wps_compatibility():
    """
    测试 WPS 兼容性
    """
    print("\n" + "=" * 60)
    print("测试 2：WPS 兼容性检查")
    print("=" * 60)
    
    temp_dir = tempfile.gettempdir()
    input_file = os.path.join(temp_dir, 'test_input.docx')
    output_file = os.path.join(temp_dir, 'test_wps.docx')
    
    try:
        # 创建测试文件
        create_test_docx(input_file)
        
        with WPSRevisionWriter(input_file, output_file) as writer:
            writer.author = "WPS 测试员"
            
            # 添加修订
            writer.add_deletion("删除内容")
            writer.add_insertion("插入内容")
            writer.add_comment("批注内容")
            
            writer.finalize()
        
        # 检查 XML 命名空间
        print("1. 检查 XML 命名空间...")
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            document_content = zip_ref.read('word/document.xml').decode('utf-8')
            
            # 检查是否包含标准命名空间
            assert 'http://schemas.openxmlformats.org/wordprocessingml/2006/main' in document_content
            print("   ✓ 包含标准 Word ML 命名空间")
        
        # 检查时间格式
        print("2. 检查时间格式...")
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            comments_content = zip_ref.read('word/comments.xml').decode('utf-8')
            
            # 检查 ISO 8601 格式
            import re
            iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
            assert re.search(iso_pattern, comments_content)
            print("   ✓ 时间格式符合 ISO 8601")
        
        # 检查 ID 唯一性
        print("3. 检查 ID 唯一性...")
        with WPSRevisionWriter(input_file, output_file) as writer:
            id1 = writer.add_comment("评论 1")
            id2 = writer.add_comment("评论 2")
            id3 = writer.add_comment("评论 3")
            
            assert id1 != id2 and id2 != id3 and id1 != id3
            print(f"   ✓ ID 唯一 (ID: {id1}, {id2}, {id3})")
        
        print("\n✓ 测试 2 通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试 2 失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        for f in [input_file, output_file]:
            if os.path.exists(f):
                os.remove(f)


def test_xml_structure():
    """
    测试 XML 结构正确性
    """
    print("\n" + "=" * 60)
    print("测试 3：XML 结构验证")
    print("=" * 60)
    
    temp_dir = tempfile.gettempdir()
    input_file = os.path.join(temp_dir, 'test_input.docx')
    output_file = os.path.join(temp_dir, 'test_xml.docx')
    
    try:
        create_test_docx(input_file)
        
        with WPSRevisionWriter(input_file, output_file) as writer:
            writer.add_deletion("测试")
            writer.add_insertion("测试")
            writer.add_comment("测试")
            writer.finalize()
        
        # 验证 XML 格式
        print("1. 验证 document.xml 格式...")
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            document_xml = zip_ref.read('word/document.xml')
            
            # 尝试解析 XML
            parser = etree.XMLParser()
            etree.fromstring(document_xml, parser)
            print("   ✓ document.xml 是有效的 XML")
        
        print("2. 验证 comments.xml 格式...")
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            if 'word/comments.xml' in zip_ref.namelist():
                comments_xml = zip_ref.read('word/comments.xml')
                etree.fromstring(comments_xml, parser)
                print("   ✓ comments.xml 是有效的 XML")
            else:
                print("   ✗ comments.xml 不存在")
                return False
        
        print("3. 验证 settings.xml 格式...")
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            settings_xml = zip_ref.read('word/settings.xml')
            etree.fromstring(settings_xml, parser)
            print("   ✓ settings.xml 是有效的 XML")
        
        print("\n✓ 测试 3 通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试 3 失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        for f in [input_file, output_file]:
            if os.path.exists(f):
                os.remove(f)


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("XML 修订痕迹写入功能测试")
    print("=" * 60)
    
    tests = [
        ("基本修订功能", test_basic_revision),
        ("WPS 兼容性", test_wps_compatibility),
        ("XML 结构", test_xml_structure)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试异常：{str(e)}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
