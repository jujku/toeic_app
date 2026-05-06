#!/usr/bin/env python3
"""
OCR 提取 PDF 页面图片中的词汇，生成 vocabulary.json
在 GitHub Actions 中运行，打包前生成完整词库
"""
import json
import os
import re
from pathlib import Path

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

def ocr_pages(img_dir: str):
    """OCR 识别所有页面图片"""
    if PaddleOCR is None:
        print("PaddleOCR 未安装，跳过 OCR")
        return []
    
    ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False, use_gpu=False)
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
    
    # 去重
    seen = set()
    unique = []
    for w in words:
        key = w["word"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(w)
    
    return unique

def parse_text(text: str):
    """解析 OCR 文本为词汇列表"""
    words = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    for line in lines:
        # 跳过字母分组标题和页码
        if re.match(r'^[A-Z]-\s*$', line) or line.isdigit():
            continue
        
        # 找到第一个中文字符分割
        match = re.search(r'[\u4e00-\u9fff]', line)
        if not match:
            continue
        
        split_pos = match.start()
        english = line[:split_pos].strip()
        chinese = line[split_pos:].strip()
        
        if not english or not chinese or len(english) < 2:
            continue
        
        # 清理
        english = re.sub(r'[^\w\s\-\']', '', english).strip()
        meanings = [m.strip() for m in re.split(r'[；;]', chinese) if m.strip()]
        
        if not meanings:
            meanings = [chinese]
        
        pos = infer_pos(meanings)
        
        words.append({
            "word": english,
            "meanings": meanings,
            "pos": pos,
            "phonetic": "",
            "toeic_sentence": ""
        })
    
    return words

def infer_pos(meanings):
    """简单词性推断"""
    text = "；".join(meanings)
    if any(m.endswith('地') for m in meanings):
        return "adv"
    if any(m.endswith('的') for m in meanings):
        if not any(v in text for v in ['使', '让', '令']):
            return "adj"
    if any(p in text for p in ['在…', '向…', '从…', '到…']):
        return "prep"
    if any(v in text for v in ['使', '做', '为', '进行', '完成']):
        return "verb"
    return "noun"

def fallback_load():
    """如果 OCR 不可用，复制预置样本为 vocabulary.json"""
    import shutil
    sample = Path("assets/vocabulary_sample.json")
    output = Path("assets/vocabulary.json")
    if sample.exists():
        shutil.copy(sample, output)
        print(f"已复制预置样本到 {output}")
    return []

def main():
    img_dir = "pdf_pages"
    output = "assets/vocabulary.json"
    
    if Path(img_dir).exists() and PaddleOCR is not None:
        words = ocr_pages(img_dir)
        print(f"共识别 {len(words)} 个唯一词汇")
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        print(f"词库已保存到 {output}")
    else:
        print("使用预置样本词库")
        fallback_load()

if __name__ == "__main__":
    main()
