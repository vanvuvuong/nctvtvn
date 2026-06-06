#!/usr/bin/env python3
"""
Thêm navWeight vào frontmatter của các file cây thuốc đã tách.
Theme sort navWeight desc, nên plant #1 cần navWeight cao nhất.
Dùng navWeight = 1000 - weight + 1
"""

import re
from pathlib import Path

BASE_DIR = Path("content/phan-2")
MAX_NAV = 1000


def process_file(filepath):
    """Thêm navWeight vào frontmatter dựa trên weight hiện có."""
    content = filepath.read_text(encoding='utf-8')

    # Tìm weight trong frontmatter
    match = re.search(r'^weight:\s*(\d+)', content, re.MULTILINE)
    if not match:
        return False

    weight = int(match.group(1))
    nav_weight = MAX_NAV - weight + 1  # #1 → 1000, #421 → 580

    # Thêm navWeight sau dòng weight
    new_content = content.replace(
        f'weight: {weight}\n',
        f'weight: {weight}\nnavWeight: {nav_weight}\n',
        1
   )

    filepath.write_text(new_content, encoding='utf-8')
    return True


def main():
    count = 0
    for subdir in sorted(BASE_DIR.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith('_'):
            continue

        for md_file in sorted(subdir.glob('*.md')):
            if md_file.name == '_index.md':
                continue
            if process_file(md_file):
                count += 1

    print(f"Updated {count} files with navWeight")


if __name__ == '__main__':
    main()
