#!/usr/bin/env python3
"""
Thêm `keywords:` vào frontmatter của mỗi bài post trong content/phan-2/*/*.md

Logic:
- Lấy tên category từ folder cha (ví dụ 2-1-benh-phu-nu → "bệnh phụ nữ")
- Lấy tên cây (Việt) từ title (ví dụ "1. ÍCH MẪU 益母草" → "ích mẫu")
- Lấy tên chữ Hán (nếu có) từ title
- Lấy tên khoa học từ dòng "Tên khoa học ..."
- Lấy các cụm công dụng bắt đầu bằng action verbs (chữa, trị, thuốc bổ, ...) trong mục E. Công dụng

Usage:
  python scripts/add-keywords.py --dry-run [file1 file2 ...]   # in ra dự kiến, không sửa
  python scripts/add-keywords.py [file1 file2 ...]             # ghi file
  python scripts/add-keywords.py --all                         # áp cho mọi file phan-2/*/*.md
"""

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"

CATEGORY_MAP = {
    "2-1-benh-phu-nu":          "bệnh phụ nữ",
    "2-2-mun-nhot-vet-thuong":  "mụn nhọt, vết thương và bệnh ngoài da",
    "2-3-giun-san":             "giun sán và ký sinh trùng",
    "2-4-ly-tieu-chay":         "lỵ và tiêu chảy",
    "2-5-tiet-nieu":            "đường tiết niệu",
    "2-6-cam-mau-tim-mach":     "cầm máu và bệnh tim mạch",
    "2-7-gian-co-doc":          "giãn cơ và thuốc độc",
    "2-8-tieu-hoa":             "đường tiêu hóa",
    "2-9-nhuan-trang-da-day":   "nhuận tràng và bệnh dạ dày",
    "2-10-xuong-khop":          "xương khớp và tê thấp",
    "2-11-cac-benh-khac":       "rắn cắn, giải độc và các bệnh khác",
    "2-12-tim-sot-ret":         "tim và sốt rét",
    "2-13-ho-hap":              "hô hấp",
    "2-14-sat-trung-bo":        "sát trùng và thuốc bổ",
    "2-15-thuoc-bo-1":          "thuốc bổ",
    "2-16-thuoc-bo-2":          "thuốc bổ và vị thuốc động vật",
}

# Pattern phát hiện chữ Hán/Nhật (CJK Unified Ideographs + Extension A)
CJK = r"[㐀-䶿一-鿿]+"

# Action keywords để filter các cụm trong mục Công dụng.
ACTION_PREFIXES = [
    "chữa", "trị", "làm thuốc", "dùng làm thuốc",
    "thuốc bổ", "thuốc thông", "thuốc lợi", "thuốc sát trùng",
    "thuốc cầm máu", "thuốc an thần", "thuốc giải độc",
    "thuốc tẩy", "thuốc xổ", "thuốc nhuận tràng",
    "bổ huyết", "bổ khí", "bổ thận", "bổ tỳ", "bổ phế", "bổ tâm",
    "bổ can", "bổ âm", "bổ dương", "bổ trung",
    "cầm máu", "sát trùng", "giải độc", "giảm đau", "tiêu viêm",
    "tiêu thũng", "tiêu đờm", "an thần", "lợi tiểu", "thông tiểu",
    "thông kinh", "điều kinh", "hoạt huyết", "phá huyết",
    "lợi sữa", "thông sữa", "thông mật", "lợi mật",
    "kích thích tiêu hóa", "giúp tiêu hóa", "kích thích",
    "tẩy giun", "tẩy sán", "trừ giun", "trừ sán",
    "hạ huyết áp", "hạ sốt", "long đờm", "trừ đờm", "trừ phong",
    "khu phong", "trừ thấp", "khử thấp",
]

# pattern to detect action prefix anywhere in text (anchored at word boundary)
ACTION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in ACTION_PREFIXES) + r")\b",
    re.IGNORECASE,
)

# boundaries that terminate a usage phrase
PHRASE_END_RE = re.compile(r"[,;.:\n\?\!]| và | hoặc | hay | với liều | dưới dạng | trong | sau ")


def parse_frontmatter(text):
    """Return (frontmatter_dict_lines, body)."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return None, text
    fm_block = m.group(1)
    body = text[m.end():]
    return fm_block, body


def extract_title(fm_block):
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm_block, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_viet_and_chinese(title):
    """
    From title like '1. ÍCH MẪU 益母草' → ('ích mẫu', '益母草')
    From title like '100. Đơn thuốc có găng tu hú' → ('đơn thuốc có găng tu hú', None)
    """
    # Strip leading "N. "
    t = re.sub(r"^\d+\.\s*", "", title).strip()
    # Extract Chinese portion
    cn_match = re.search(CJK, t)
    cn = cn_match.group(0) if cn_match else None
    # Vietnamese portion = everything before Chinese (or whole if no Chinese)
    viet = re.sub(CJK, "", t).strip()
    # remove trailing dashes/punct
    viet = re.sub(r"[\-–—()\[\]\s]+$", "", viet).strip()
    viet = viet.lower()
    return viet, cn


SCI_NAME_RE = re.compile(
    r"^T[êe]n khoa h[ọo]c[^\n]*?[_\*]+([A-Z][A-Za-z\.\-\s]+?(?:[a-z]+))[_\*]",
    re.MULTILINE,
)


def extract_scientific(body):
    """
    Look for the first 'Tên khoa học _*Foo bar*_' line.
    Return the binomial-ish string, or None.
    """
    # Find the line first.
    line_m = re.search(r"^T[êe]n khoa h[ọo]c\s*(.+)$", body, re.MULTILINE)
    if not line_m:
        return None
    line = line_m.group(1)
    # Strip markdown emphasis chars; keep letters/digits/spaces/dots/dashes
    cleaned = re.sub(r"[_*]+", "", line)
    # Take content up to first comma/parenthesis/semicolon
    cleaned = re.split(r"[,;(]", cleaned, maxsplit=1)[0]
    cleaned = cleaned.strip(" .")
    # Validate: first word should be Capitalized Latin word
    m = re.match(r"^([A-Z][a-zA-Z\-]+(?:\s+[a-zA-Z][a-zA-Z\-\.]*){1,4})", cleaned)
    if m:
        return m.group(1).strip(" .")
    # fallback: first 2-3 words
    parts = cleaned.split()
    if parts and parts[0][:1].isupper():
        return " ".join(parts[:3]).strip(" .")
    return None


# Section heading pattern for "Công dụng" (handles 3, 4, or 5 hashes; with/without dot suffix)
USAGE_HEADING = re.compile(
    r"^#{3,5}\s*[A-Z]\.\s*C[ôo]ng d[ụu]ng[^\n]*$",
    re.MULTILINE,
)
NEXT_HEADING = re.compile(r"^#{1,5}\s+\S", re.MULTILINE)


def extract_usage_section(body):
    m = USAGE_HEADING.search(body)
    if not m:
        # No formal section: use the whole body (small posts like "Đơn thuốc có ...")
        return body
    start = m.end()
    # Find next heading or end
    nxt = NEXT_HEADING.search(body, start)
    end = nxt.start() if nxt else len(body)
    return body[start:end]


# Match dosage / prescription-like content to exclude
DOSAGE_RE = re.compile(
    r"\b\d+\s*(?:g|gam|kg|ml|mg|lạng|chén|bát|nắm|thìa|muỗng|liều|lần|ngày|tháng|giờ|phút)\b",
    re.IGNORECASE,
)


def extract_usage_keywords(usage_text, limit=10):
    """Find phrases that BEGIN with action verbs (chữa, trị, thuốc bổ, ...).
    Strategy: for each occurrence of an action verb, extract from verb to next
    phrase-terminating punctuation."""
    # Strip markdown emphasis and links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", usage_text)  # md links
    text = re.sub(r"[_*`]+", "", text)
    text = re.sub(r"\s+", " ", text)

    keywords = []
    seen = set()
    for m in ACTION_RE.finditer(text):
        start = m.start()
        # Find next boundary after the verb
        rest = text[start:]
        end_m = PHRASE_END_RE.search(rest, 1)  # skip the verb itself
        phrase = rest[: end_m.start()] if end_m else rest
        phrase = phrase.strip(" -:–—\"'()")

        # Sanity checks
        if len(phrase) < 5 or len(phrase) > 80:
            continue
        # Exclude phrases that look like prescriptions (have dosages)
        if DOSAGE_RE.search(phrase):
            continue
        # Skip phrases ending mid-word (basic check: shouldn't end with conjunctions)
        low = phrase.lower()
        if low.endswith((" và", " hoặc", " hay", " của", " trong")):
            continue

        norm = re.sub(r"\s+", " ", phrase).strip().lower()
        # Balance parens
        if norm.count(")") > norm.count("("):
            norm = norm.rstrip(")")
        if norm.count("(") > norm.count(")"):
            norm = norm[: norm.rfind("(")].strip()
        # trim trailing filler words
        norm = re.sub(r"\s+(?:có|không|rồi|nữa|lại|cũng)$", "", norm).strip()
        if len(norm) < 5:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        keywords.append(norm)

    # Substring dedup: if A is contained in B, keep the shorter one A.
    keywords.sort(key=len)
    pruned = []
    for kw in keywords:
        if any(kw != p and kw in p for p in pruned):
            continue
        # Also drop if there's a shorter substring already in pruned
        if any(p in kw and p != kw for p in pruned):
            continue
        pruned.append(kw)
    return pruned[:limit]


def build_keywords(path, fm_block, body):
    folder = path.parent.name
    category = CATEGORY_MAP.get(folder)

    title = extract_title(fm_block)
    viet, cn = extract_viet_and_chinese(title)
    sci = extract_scientific(body)
    usage_text = extract_usage_section(body)
    usage_kws = extract_usage_keywords(usage_text)

    keywords = []
    if category:
        keywords.append(category)
    if viet:
        keywords.append(viet)
    if sci:
        keywords.append(sci)
    if cn:
        keywords.append(cn)
    for kw in usage_kws:
        if kw not in keywords:
            keywords.append(kw)
    return keywords


def fm_already_has_keywords(fm_block):
    return re.search(r"^keywords:\s*$", fm_block, re.MULTILINE) is not None \
        or re.search(r"^keywords:\s*\[", fm_block, re.MULTILINE) is not None


def update_frontmatter(fm_block, keywords):
    """Inject keywords block before the closing line (replace existing if any)."""
    # Remove existing keywords block first
    fm_block = re.sub(
        r"^keywords:\s*(?:\[.*?\]|\n(?:[ \t]+-[^\n]*\n?)+)",
        "",
        fm_block,
        flags=re.MULTILINE | re.DOTALL,
   ).rstrip()

    # Format new block
    lines = ["keywords:"]
    for kw in keywords:
        # YAML: quote if contains : or starts with special chars
        if any(c in kw for c in [":", "#", "'", "\""]) or kw.strip() != kw:
            esc = kw.replace('"', '\\"')
            lines.append(f'  - "{esc}"')
        else:
            lines.append(f"  - {kw}")
    new_block = fm_block + "\n" + "\n".join(lines)
    return new_block


def process_file(path: Path, dry_run: bool):
    text = path.read_text(encoding="utf-8")
    fm_block, body = parse_frontmatter(text)
    if fm_block is None:
        return None  # skip
    keywords = build_keywords(path, fm_block, body)
    new_fm = update_frontmatter(fm_block, keywords)
    new_text = f"---\n{new_fm}\n---\n{body}"
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return keywords


def iter_target_files():
    for sub in sorted(CONTENT_DIR.glob("phan-2/2-*")):
        if not sub.is_dir():
            continue
        for f in sorted(sub.glob("*.md")):
            if f.name == "_index.md":
                continue
            yield f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="Specific files to process")
    ap.add_argument("--all", action="store_true", help="Process all files in phan-2/")
    ap.add_argument("--dry-run", action="store_true", help="Print, do not write")
    args = ap.parse_args()

    if args.all:
        targets = list(iter_target_files())
    elif args.files:
        targets = [Path(f).resolve() for f in args.files]
    else:
        ap.error("Provide files or --all")

    total = 0
    for p in targets:
        kws = process_file(p, args.dry_run)
        if kws is None:
            print(f"SKIP {p} (no frontmatter)")
            continue
        total += 1
        try:
            rel = p.relative_to(REPO)
        except ValueError:
            rel = p
        print(f"\n## {rel}")
        for k in kws:
            print(f"  - {k}")
    print(f"\n{total} files {'previewed' if args.dry_run else 'updated'}.")


if __name__ == "__main__":
    main()
