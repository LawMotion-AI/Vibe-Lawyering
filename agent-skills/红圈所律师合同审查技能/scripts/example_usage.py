"""
合同审核 XML 修订痕迹写入 - 使用示例

这个脚本演示了如何使用 WPSRevisionWriter 来为合同文档添加修订痕迹。
"""

import os
import sys
from datetime import datetime

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from internal_write_revisions_xml import WPSRevisionWriter


def example_basic_revision():
    """
    基本示例：添加删除、插入和批注
    """
    print("=" * 60)
    print("示例 1：基本修订操作")
    print("=" * 60)
    
    input_file = 'test_input.docx'
    output_file = 'test_output_revised.docx'
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：输入文件 '{input_file}' 不存在")
        print("请创建一个测试用的 DOCX 文件")
        return
    
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")
    
    with WPSRevisionWriter(input_file, output_file) as writer:
        # 设置作者信息
        writer.author = "合同审核律师"
        
        # 示例 1：添加删除标记
        print("\n1. 添加删除标记...")
        del_xml = writer.add_deletion(
            text="原条款内容",
            author="合同审核律师",
            date="2026-03-19T10:00:00Z"
        )
        print(f"   删除标记 XML: {del_xml[:100]}...")
        
        # 示例 2：添加插入标记
        print("\n2. 添加插入标记...")
        ins_xml = writer.add_insertion(
            text="修订后条款内容",
            author="合同审核律师",
            date="2026-03-19T10:00:00Z"
        )
        print(f"   插入标记 XML: {ins_xml[:100]}...")
        
        # 示例 3：添加批注
        print("\n3. 添加批注...")
        comment_text = """问题：该条款责任边界不清
风险：可能导致违约责任无法明确划分
建议：修改为"违约方应承担因其违约行为给守约方造成的全部直接损失"
法律依据：《民法典》第五百七十七条"""
        
        comment_id = writer.add_comment(
            comment_text=comment_text,
            author="合同审核律师",
            date="2026-03-19T10:00:00Z"
        )
        print(f"   批注 ID: {comment_id}")
        
        # 示例 4：添加多个批注
        print("\n4. 添加更多批注...")
        for i in range(2, 5):
            comment_id = writer.add_comment(
                comment_text=f"批注示例 {i}：这是第{i}个批注内容",
                author="合同审核律师"
            )
            print(f"   批注 ID: {comment_id}")
        
        # 完成修订
        print("\n5. 完成修订并保存...")
        writer.finalize()
    
    print(f"\n✓ 修订完成！输出文件：{output_file}")
    print("请在 WPS Office 中打开查看修订效果")


def example_contract_review():
    """
    合同审核示例：模拟真实的合同审核场景
    """
    print("\n" + "=" * 60)
    print("示例 2：合同审核场景")
    print("=" * 60)
    
    input_file = 'contract_original.docx'
    output_file = 'contract_revised.docx'
    
    if not os.path.exists(input_file):
        print(f"错误：输入文件 '{input_file}' 不存在")
        return
    
    with WPSRevisionWriter(input_file, output_file) as writer:
        writer.author = "法务审核部"
        
        # 场景 1：修改违约责任条款
        print("\n1. 修改违约责任条款...")
        
        # 删除原条款
        original_text = "违约方应承担相应的违约责任"
        del_xml = writer.add_deletion(
            text=original_text,
            author="法务审核部",
            date=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        )
        
        # 插入新条款
        revised_text = "违约方应赔偿因其违约行为给守约方造成的全部损失，包括但不限于直接损失、预期利益损失以及为维权支出的合理费用（律师费、诉讼费、保全费等）"
        ins_xml = writer.add_insertion(
            text=revised_text,
            author="法务审核部",
            date=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        )
        
        # 添加批注说明
        comment1 = """【问题】原条款违约责任约定过于笼统
【风险】
1. "相应责任"表述不明确，实践中容易产生争议
2. 未明确赔偿范围，可能无法覆盖全部损失
3. 未明确维权费用承担，增加守约方维权成本
【修改建议】
细化违约责任承担方式，明确赔偿范围包括直接损失、间接损失及维权费用
【法律依据】
《民法典》第五百七十七条、第五百八十四条"""
        
        writer.add_comment(comment1)
        
        # 场景 2：修改争议解决条款
        print("2. 修改争议解决条款...")
        
        original_dispute = "争议由双方协商解决，协商不成的，向原告所在地人民法院起诉"
        revised_dispute = "争议由双方协商解决，协商不成的，任何一方均有权向被告所在地有管辖权的人民法院提起诉讼"
        
        writer.add_deletion(original_dispute)
        writer.add_insertion(revised_dispute)
        
        comment2 = """【问题】管辖法院约定不明确
【风险】
1. "原告所在地"在起诉前无法确定，可能导致管辖权争议
2. 未明确"有管辖权"，可能因级别管辖问题被驳回
【修改建议】
明确为"被告所在地"，符合"原告就被告"的一般管辖原则
【实务提示】
如希望约定对我方有利的管辖法院，可明确约定为"我方所在地人民法院" """
        
        writer.add_comment(comment2)
        
        # 场景 3：修改保密条款
        print("3. 修改保密条款...")
        
        original_confidential = "双方应对本合同内容保密"
        revised_confidential = "双方应对本合同内容及在合同履行过程中知悉的对方商业秘密、技术秘密、客户信息等保密信息承担保密义务，未经对方书面同意，不得向任何第三方披露，法律法规另有规定或监管机构另有要求的除外"
        
        writer.add_deletion(original_confidential)
        writer.add_insertion(revised_confidential)
        
        comment3 = """【问题】保密义务范围过窄
【风险】
1. 仅约定"合同内容"保密，范围过窄
2. 未明确保密信息的具体类型
3. 未规定例外情形
【修改建议】
扩大保密范围至合同履行过程中知悉的所有保密信息，并明确例外情形
【参考】
可进一步约定保密期限、违约责任等"""
        
        writer.add_comment(comment3)
        
        # 完成
        print("4. 完成修订...")
        writer.finalize()
    
    print(f"\n✓ 合同审核完成！输出文件：{output_file}")
    print("\n修订内容摘要：")
    print("  - 违约责任条款：已修改并添加批注")
    print("  - 争议解决条款：已修改并添加批注")
    print("  - 保密条款：已修改并添加批注")
    print("\n请在 WPS Office 中打开查看，并检查：")
    print("  1. 删除内容是否显示删除线")
    print("  2. 插入内容是否显示下划线")
    print("  3. 批注是否正确显示在批注框中")


def example_batch_comments():
    """
    批量添加批注示例
    """
    print("\n" + "=" * 60)
    print("示例 3：批量添加批注")
    print("=" * 60)
    
    input_file = 'contract_draft.docx'
    output_file = 'contract_with_comments.docx'
    
    if not os.path.exists(input_file):
        print(f"错误：输入文件 '{input_file}' 不存在")
        return
    
    # 准备批注列表
    comments = [
        {
            'location': '第一条 定义条款',
            'text': """【问题】定义词使用不规范
【具体意见】
1. "甲方"、"乙方"应统一使用全称或定义后的简称
2. 首次出现时应加引号或标注
3. 后文应保持一致，避免混用"""
        },
        {
            'location': '第三条 付款条款',
            'text': """【问题】付款条件不明确
【风险】
1. 未明确付款时间节点
2. 未约定发票开具时间
3. 未规定逾期付款违约责任
【建议】补充：
- 付款期限：收到发票后 X 个工作日内
- 逾期违约金：每日万分之五"""
        },
        {
            'location': '第五条 知识产权',
            'text': """【问题】知识产权归属约定不完整
【风险】
1. 未明确背景知识产权归属
2. 未约定履行过程中产生的知识产权归属
3. 未规定知识产权侵权责任承担
【建议】区分：
- 背景知识产权：归各自所有
- 新产生知识产权：约定归属或使用许可"""
        },
        {
            'location': '第七条 合同解除',
            'text': """【问题】解除权行使条件过于宽泛
【风险】
1. "严重违约"标准不明确
2. 未约定解除通知期限
3. 未规定合同解除后的处理
【建议】明确：
- 具体违约情形
- 书面通知 + 合理期限
- 恢复原状、赔偿损失等后果"""
        },
        {
            'location': '第九条 不可抗力',
            'text': """【问题】不可抗力条款不完整
【具体意见】
1. 未明确通知义务和证明责任
2. 未规定不可抗力持续期间的处理
3. 未明确不可抗力免责范围
【建议】补充：
- 及时通知 + 提供证明
- 持续 X 天可解除合同
- 仅免除迟延履行责任"""
        }
    ]
    
    with WPSRevisionWriter(input_file, output_file) as writer:
        writer.author = "合同审核专员"
        
        print(f"\n开始批量添加 {len(comments)} 个批注...")
        
        for i, comment in enumerate(comments, 1):
            print(f"  {i}. 添加批注：{comment['location']}")
            
            full_comment = f"【位置】{comment['location']}\n\n{comment['text']}"
            comment_id = writer.add_comment(full_comment)
            
            print(f"     批注 ID: {comment_id}")
        
        print("\n完成批注添加...")
        writer.finalize()
    
    print(f"\n✓ 批量批注完成！输出文件：{output_file}")
    print(f"共添加 {len(comments)} 个批注")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("合同审核 XML 修订痕迹写入 - 使用示例")
    print("=" * 60)
    print("\n请选择要运行的示例：")
    print("1. 基本修订操作示例")
    print("2. 合同审核场景示例")
    print("3. 批量添加批注示例")
    print("0. 退出")
    
    choice = input("\n请输入选项 (0-3): ").strip()
    
    if choice == '1':
        example_basic_revision()
    elif choice == '2':
        example_contract_review()
    elif choice == '3':
        example_batch_comments()
    elif choice == '0':
        print("再见！")
    else:
        print("无效的选项")


if __name__ == '__main__':
    main()
