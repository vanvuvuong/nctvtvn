#!/usr/bin/env python3
"""
Tách các file markdown lớn trong phan-2 thành từng file riêng cho mỗi cây thuốc.
Đánh số toàn cục 1, 2, 3, ... để đóng sách điện tử.

Cấu trúc output:
  content/phan-2/
    2-1-benh-phu-nu/
      _index.md              (intro của chương)
      0001-ich-mau.md        (cây thuốc #1)
      0002-huong-phu.md      (cây thuốc #2)
      ...
    2-2-mun-nhot-vet-thuong/
      _index.md
      0028-bo-cong-anh.md
      ...
"""

import re
from pathlib import Path

BASE_DIR = Path("content/phan-2")
BACKUP_DIR = Path("content/phan-2/_original")

FILES_ORDER = [
    "2-1-benh-phu-nu.md",
    "2-2-mun-nhot-vet-thuong.md",
    "2-3-giun-san.md",
    "2-4-ly-tieu-chay.md",
    "2-5-tiet-nieu.md",
    "2-6-cam-mau-tim-mach.md",
    "2-7-gian-co-doc.md",
    "2-8-tieu-hoa.md",
    "2-9-nhuan-trang-da-day.md",
    "2-10-xuong-khop.md",
    "2-11-cac-benh-khac.md",
    "2-12-tim-sot-ret.md",
    "2-13-ho-hap.md",
    "2-14-sat-trung-bo.md",
    "2-15-thuoc-bo-1.md",
    "2-16-thuoc-bo-2.md",
]

# Vietnamese diacritics → ASCII for slugs
_VIET_PAIRS = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'đ': 'd',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
}
# Add uppercase versions
_VIET_PAIRS.update({k.upper(): v for k, v in _VIET_PAIRS.items()})
_VIET_MAP = str.maketrans(_VIET_PAIRS)


def slugify(text):
    """Tạo slug URL-friendly từ tên tiếng Việt."""
    # Bỏ chữ Hán
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf]+', '', text)
    # Chuyển tiếng Việt → ASCII
    text = text.translate(_VIET_MAP).lower()
    # Chỉ giữ a-z, 0-9, space, hyphen
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Space/multi-hyphen → single hyphen
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text or 'entry'


def parse_file(filepath):
    """Đọc file markdown, tách frontmatter, intro, và các entry."""
    content = filepath.read_text(encoding='utf-8')

    # Tách frontmatter
    fm = {}
    body = content
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            for line in content[3:end].strip().split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    fm[key.strip()] = val.strip()
            body = content[end + 3:].lstrip('\n')

    # Split theo ### heading
    parts = re.split(r'^(### .+)$', body, flags=re.MULTILINE)

    intro = parts[0]
    entries = []
    for i in range(1, len(parts), 2):
        heading = parts[i][4:]  # Bỏ "### "
        entry_content = parts[i + 1] if i + 1 < len(parts) else ""
        entries.append((heading, entry_content))

    return fm, intro, entries


def fix_images(content):
    """Chuyển image path từ relative sang absolute."""
    return re.sub(r'\(images/', '(/images/', content)


def yaml_escape(text):
    """Escape title cho YAML double-quoted string."""
    return text.replace('\\', '\\\\').replace('"', '\\"')


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    counter = 1
    summary = []

    for filename in FILES_ORDER:
        filepath = BASE_DIR / filename
        if not filepath.exists():
            print(f"[SKIP] {filename} - không tìm thấy")
            continue

        dirname = filename[:-3]  # Bỏ .md
        outdir = BASE_DIR / dirname
        outdir.mkdir(exist_ok=True)

        fm, intro, entries = parse_file(filepath)
        author = fm.get('author', 'Giáo sư Tiến sĩ Đỗ Tất Lợi')
        title = fm.get('title', dirname)
        desc = fm.get('description', '')

        # Ghi _index.md cho chương
        index_path = outdir / '_index.md'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(f'---\n')
            f.write(f'title: "{yaml_escape(title)}"\n')
            f.write(f'description: "{yaml_escape(desc)}"\n')
            f.write(f'author: {author}\n')
            f.write(f'---\n\n')
            f.write(fix_images(intro))

        # Ghi từng cây thuốc
        start_num = counter
        for heading, entry_content in entries:
            slug = slugify(heading)
            entry_filename = f"{counter:04d}-{slug}.md"

            entry_path = outdir / entry_filename
            with open(entry_path, 'w', encoding='utf-8') as f:
                f.write(f'---\n')
                f.write(f'title: "{counter}. {yaml_escape(heading)}"\n')
                f.write(f'weight: {counter}\n')
                f.write(f'author: {author}\n')
                f.write(f'---\n\n')
                f.write(fix_images(entry_content))

            counter += 1

        end_num = counter - 1
        count = end_num - start_num + 1
        print(f"[OK] {filename} → {dirname}/ ({count} mục, #{start_num}–#{end_num})")
        summary.append((dirname, count, start_num, end_num))

        # Di chuyển file gốc vào _original/
        filepath.rename(BACKUP_DIR / filename)

    total = counter - 1
    print(f"\n{'=' * 50}")
    print(f"Tổng cộng: {total} cây thuốc/vị thuốc")
    print(f"File gốc đã chuyển vào: {BACKUP_DIR}/")
    print(f"{'=' * 50}")

    # Ghi summary
    with open(BASE_DIR / '_split-summary.txt', 'w', encoding='utf-8') as f:
        f.write(f"Tổng: {total} mục\n\n")
        for dirname, count, start, end in summary:
            f.write(f"{dirname}: {count} mục (#{start}–#{end})\n")


if __name__ == '__main__':
    main()
