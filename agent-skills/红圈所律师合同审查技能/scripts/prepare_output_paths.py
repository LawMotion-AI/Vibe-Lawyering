#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print('用法: prepare_output_paths.py <原合同路径>')
        sys.exit(1)

    source = Path(sys.argv[1]).resolve()
    stem = source.stem
    output_dir = source.parent / f'{stem}-Output'
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        'source': str(source),
        'output_dir': str(output_dir),
        'reviewed_docx': str(output_dir / f'{stem}-修订批注版.docx'),
        'optional_clean_docx': str(output_dir / f'{stem}-清洁版.docx'),
        'comment_language': '简体中文',
        'comment_font': '宋体',
        'comment_font_ooxml': 'SimSun',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
