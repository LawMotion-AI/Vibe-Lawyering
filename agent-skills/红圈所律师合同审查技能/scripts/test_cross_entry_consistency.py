import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from shutil import which

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_xml_revision import collect_docx_summary, create_test_docx
from internal_write_revisions_xml import create_revision_from_json


def resolve_powershell_executable() -> str:
    for candidate in ('pwsh', 'powershell', 'powershell.exe'):
        executable = which(candidate)
        if executable:
            return executable
    raise RuntimeError('未找到可用的 PowerShell 可执行文件（pwsh / powershell / powershell.exe）')


def run_case(
    repo_root: str,
    powershell_executable: str,
    generate_script: str,
    temp_dir: str,
    case_name: str,
    payload: dict,
) -> None:
    source_docx = os.path.join(temp_dir, f'{case_name}-source.docx')
    instructions_json = os.path.join(temp_dir, f'{case_name}-instructions.json')
    python_output = os.path.join(temp_dir, f'{case_name}-python-reviewed.docx')
    powershell_output = os.path.join(temp_dir, f'{case_name}-powershell-reviewed.docx')

    create_test_docx(source_docx)
    with open(instructions_json, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    create_revision_from_json(source_docx, python_output, json.dumps(payload, ensure_ascii=False))

    command = [
        powershell_executable,
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        generate_script,
        '-Source',
        source_docx,
        '-Instructions',
        instructions_json,
        '-Output',
        powershell_output,
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=repo_root
    )
    if result.returncode != 0:
        raise RuntimeError(
            f'PowerShell 路径执行失败（{case_name}）\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}'
        )

    python_summary = collect_docx_summary(python_output)
    powershell_summary = collect_docx_summary(powershell_output)

    comparable_keys = [
        'del_count',
        'ins_count',
        'comment_range_start_count',
        'comment_range_end_count',
        'comment_reference_count',
        'track_revisions',
        'show_revisions',
        'comment_texts',
        'paragraph_texts',
        'visible_paragraph_texts',
        'comment_font_locked',
        'has_comments_rel',
        'has_settings_rel',
        'has_comments_override',
        'has_settings_override',
    ]
    comparable_python = {key: python_summary[key] for key in comparable_keys}
    comparable_powershell = {key: powershell_summary[key] for key in comparable_keys}

    if comparable_python != comparable_powershell:
        raise AssertionError(
            'Python 与 PowerShell 输出摘要不一致\n'
            f'Case: {case_name}\n'
            f'Python:\n{json.dumps(comparable_python, ensure_ascii=False, indent=2, sort_keys=True)}\n'
            f'PowerShell:\n{json.dumps(comparable_powershell, ensure_ascii=False, indent=2, sort_keys=True)}\n'
            f'完整 Python 摘要：\n{json.dumps(python_summary, ensure_ascii=False, indent=2, sort_keys=True)}\n'
            f'完整 PowerShell 摘要：\n{json.dumps(powershell_summary, ensure_ascii=False, indent=2, sort_keys=True)}'
        )

    if case_name == 'anchor':
        expected_comment = (
            '问题：原文表述过于口语化\n'
            '风险：正式合同文本不够严谨\n'
            '修改建议：改为完成态表述\n'
            '建议条款：这是第二段文本内容，已经修改完成'
        )
        actual_comment = python_summary['comment_texts'][0]
        if actual_comment != expected_comment:
            raise AssertionError(
                '批注文本出现意外空格或内容漂移\n'
                f'Case: {case_name}\n'
                f'Actual: {actual_comment!r}\n'
                f'Expected: {expected_comment!r}'
            )

    print(f'✓ Case {case_name} 一致（PowerShell: {powershell_executable}）')
    print(json.dumps({
        'del_count': comparable_python['del_count'],
        'ins_count': comparable_python['ins_count'],
        'comment_range_start_count': comparable_python['comment_range_start_count'],
        'comment_range_end_count': comparable_python['comment_range_end_count'],
        'comment_reference_count': comparable_python['comment_reference_count'],
        'show_revisions': comparable_python['show_revisions'],
        'track_revisions': comparable_python['track_revisions'],
        'visible_paragraph_texts': comparable_python['visible_paragraph_texts'],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    if case_name == 'anchor':
        print(f'anchor_comment_sha256={hashlib.sha256(actual_comment.encode("utf-8")).hexdigest()}')


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_script = os.path.join(repo_root, 'scripts', 'run_generate_review_docx.ps1')
    powershell_executable = resolve_powershell_executable()
    temp_dir = tempfile.mkdtemp(prefix='cross-entry-')
    try:
        cases = [
            (
                'anchor',
                {
                    'author': '跨入口一致性测试',
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
                            'match_type': 'exact',
                            'occurrence': 1,
                            'comment': {
                                '问题': '第三段需要后续人工确认',
                                '风险': '上下文衔接不足',
                                '修改建议': '补强关联条款'
                            }
                        }
                    ]
                }
            ),
            (
                'location',
                {
                    'author': '跨入口一致性测试',
                    'date': '2026-03-19T10:00:00Z',
                    'operations': [
                        {
                            'mode': 'revision',
                            'location': {'paragraph': 1},
                            'replacement_text': '这是第一段文本内容（location 一致性测试）'
                        },
                        {
                            'mode': 'comment',
                            'location': {'paragraph': 3},
                            'comment': {
                                '问题': '第三段需要后续人工确认',
                                '风险': '上下文衔接不足',
                                '修改建议': '补强关联条款'
                            }
                        }
                    ]
                }
            )
        ]

        for case_name, payload in cases:
            run_case(
                repo_root=repo_root,
                powershell_executable=powershell_executable,
                generate_script=generate_script,
                temp_dir=temp_dir,
                case_name=case_name,
                payload=payload
            )

        print(f'✓ Python 与 PowerShell 两条入口输出一致（PowerShell: {powershell_executable}）')
        return 0
    except Exception as exc:
        print(str(exc))
        return 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
