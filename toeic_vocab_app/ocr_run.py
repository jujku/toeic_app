import json
import os
import re
from pathlib import Path
from paddleocr import PaddleOCR

IMG_DIR = r"E:\toeic_vocab_app\pdf_pages"
OUTPUT = r"E:\toeic_vocab_app\assets\vocabulary.json"

def ocr_pages(img_dir):
    ocr = PaddleOCR(lang='ch')
    words = []
    img_files = sorted(Path(img_dir).glob("*.png"))
    
    for img_path in img_files:
        print(f"OCR: {img_path.name}")
        result = ocr.ocr(str(img_path), cls=True)
        if result and result[0]:
            page_text = "\n".join([line[1][0] for line in result[0]])
            page_words = parse_text(page_text)
            print(f"  -> {len(page_words)} 个词汇")
            words.extend(page_words)
    
    seen = set()
    unique = []
    for w in words:
        key = w["word"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique

def parse_text(text):
    words = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        if re.match(r'^[A-Z]-\s*$', line) or line.isdigit():
            continue
        match = re.search(r'[\u4e00-\u9fff]', line)
        if not match:
            continue
        split_pos = match.start()
        english = line[:split_pos].strip()
        chinese = line[split_pos:].strip()
        if not english or not chinese or len(english) < 2:
            continue
        english = re.sub(r'[^\w\s\-\']', '', english).strip()
        meanings = [m.strip() for m in re.split(r'[\uFF1B;]', chinese) if m.strip()]
        if not meanings:
            meanings = [chinese]
        pos = infer_pos(meanings)
        words.append({"word": english, "meanings": meanings, "pos": pos, "phonetic": "", "toeic_sentence": ""})
    return words

def infer_pos(meanings):
    text = "\uFF1B".join(meanings)
    if any(m.endswith('\u5730') for m in meanings):
        return "adv"
    if any(m.endswith('\u7684') for m in meanings):
        if not any(v in text for v in ['\u4F7F', '\u8BA9', '\u4EE4']):
            return "adj"
    if any(p in text for p in ['\u5728\u2026', '\u5411\u2026', '\u4ECE\u2026', '\u5230\u2026']):
        return "prep"
    if any(v in text for v in ['\u4F7F', '\u505A', '\u4E3A', '\u8FDB\u884C', '\u5B8C\u6210']):
        return "verb"
    return "noun"

if __name__ == "__main__":
    words = ocr_pages(IMG_DIR)
    print(f"\n共识别 {len(words)} 个唯一词汇")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    print(f"已保存到 {OUTPUT}")
