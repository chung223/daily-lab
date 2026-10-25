#!/usr/bin/env python3
"""
EDMoms 驗證碼破解腳本
===========================
痛點：EDMoms 公文系統登入時的驗證碼（verifyCode）無法被 OCR 識別，
      導致整個公文同步流程卡住（累計 12+ 次失敗，見 2026-09-18 recap）。

策略：
  1. 用 Playwright 截圖取得驗證碼圖片（繞過 Tesseract/RapidOCR 對扭曲字體的失敗）
  2. 截圖後用 MLX OCR（DeepSeek-OCR-2-bf16）本地端辨識（透過 uvx）
  3. 若 MLX OCR 失敗，降級用 Tesseract + 影像前處理（灰度、二值化、去噪）

用法：
  python3 edmom_captcha_solve.py --auto           # 自動從 Chrome 截圖然後解
  python3 edmom_captcha_solve.py -i /path/to/img  # 解指定圖片
"""

import os
import sys
import re
import time
import tempfile
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

# ============================================================
# OCR 引擎
# ============================================================

def ocr_with_mlx(image_path: str) -> str:
    """用 DeepSeek-OCR-2-bf16（uvx）辨識驗證碼圖片"""
    try:
        # 用 uvx 執行獨立的 MLX OCR 腳本，避免 import 衝突
        script = f"""
import os, sys
os.environ["HF_HUB_TRUST_REMOTE_CODE"] = "1"
os.environ["LOG_LEVEL"] = "WARNING"
from mlx_vlm import load, generate
model, processor = load("mlx-community/DeepSeek-OCR-2-bf16", trust_remote_code=True)
prompt = "<image>\\n請直接輸出圖中驗證碼的文字，不要其他說明。"
result = generate(model, processor, prompt=prompt, image="{image_path}")
print(result.text.strip())
"""
        result = subprocess.run(
            ['uvx', '--quiet', 'mlx-vlm', '--', 'python3', '-c', script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return f"[MLX 失敗] {result.stderr.strip()[:100]}"
    except subprocess.TimeoutExpired:
        return "[MLX 逾時]"
    except Exception as e:
        return f"[MLX 錯誤] {e}"


def ocr_with_tesseract(image_path: str) -> str:
    """用 Tesseract + 影像前處理辨識驗證碼"""
    try:
        img = Image.open(image_path).convert('L')  # 灰度

        # 簡單二值化
        img = img.point(lambda x: 0 if x < 140 else 255)

        # 放大圖片（驗證碼需要較高解析度）
        w, h = img.size
        img = img.resize((w * 3, h * 3), Image.LANCZOS)

        import pytesseract
        text = pytesseract.image_to_string(
            img,
            config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )
        return text.strip()
    except Exception as e:
        return f"[Tesseract 錯誤] {e}"


def clean_captcha(text: str) -> str:
    """只留驗證碼格式的字元（4-8位英文數字）"""
    return re.sub(r'[^A-Za-z0-9]', '', text)


def solve_captcha(image_path: str) -> str:
    """
    嘗試用 MLX OCR → Tesseract 順序解驗證碼
    """
    print(f"\n📷 輸入圖片: {image_path}")

    # Step 1: MLX OCR (uvx)
    print("🔄 嘗試 MLX OCR（DeepSeek-OCR-2-bf16）...")
    start = time.time()
    result1 = ocr_with_mlx(image_path)
    elapsed = time.time() - start
    print(f"   MLX OCR（{elapsed:.1f}s）: {result1}")
    cleaned1 = clean_captcha(result1)

    if 4 <= len(cleaned1) <= 8:
        print(f"✅ MLX OCR 成功: {cleaned1}")
        return cleaned1

    # Step 2: Tesseract 降級
    print("⚠️ MLX OCR 結果不理想，嘗試 Tesseract...")
    result2 = ocr_with_tesseract(image_path)
    print(f"   Tesseract: {result2}")
    cleaned2 = clean_captcha(result2)

    if 4 <= len(cleaned2) <= 8:
        print(f"✅ Tesseract 成功: {cleaned2}")
        return cleaned2

    print(f"❌ 兩種 OCR 均失敗")
    # 回傳最長的有效猜測
    candidates = [c for c in [cleaned1, cleaned2, clean_captcha(result1), clean_captcha(result2)] if 4 <= len(c) <= 8]
    if candidates:
        best = max(candidates, key=len)
        print(f"   降級使用最長候選: {best}")
        return best
    return cleaned1 or result1


# ============================================================
# 從 Chrome 截圖
# ============================================================

def capture_captcha_from_page(cdp_url: str = "http://localhost:18792") -> tuple[str, str]:
    """
    連接到已開啟的 Chrome，截圖驗證碼圖片。
    回傳 (screenshot_path, page_url)
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page = context.pages[0]

            # 常見驗證碼元素 selector
            captcha_sel = None
            for sel in [
                '#verifyCodeImg', '#imgVerify', '#captchaImg', '#verify_code',
                'img[id*="verify"]', 'img[id*="Verify"]', 'img[id*="captcha"]',
                'img[id*="Captcha"]', 'img[id*="code"]', '//img[contains(@src,"verify")]'
            ]:
                try:
                    el = page.query_selector(sel)
                    if el:
                        captcha_sel = sel
                        break
                except:
                    pass

            if not captcha_sel:
                print("[資訊] 無法自動定位驗證碼圖片，截圖整頁後手動裁切")
                screenshot_path = tempfile.mktemp(suffix='.png')
                page.screenshot(path=screenshot_path)
                return screenshot_path, page.url

            box = page.query_selector(captcha_sel).bounding_box()
            if not box:
                raise RuntimeError(f"驗證碼元素 {captcha_sel} 無法取得邊界")

            # 擴大範圍
            x = max(0, int(box['x'] - 5))
            y = max(0, int(box['y'] - 5))
            width = int(box['width'] + 10)
            height = int(box['height'] + 10)

            screenshot_path = tempfile.mktemp(suffix='.png')
            page.screenshot(path=screenshot_path, clip={'x': x, 'y': y, 'width': width, 'height': height})
            print(f"[成功] 驗證碼截圖已存: {screenshot_path}")
            return screenshot_path, page.url

        except Exception as e:
            raise RuntimeError(f"無法連接 Chrome CDP 或截圖: {e}")


# ============================================================
# 主程式
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='EDMoms 驗證碼破解')
    parser.add_argument('--image', '-i', default=None, help='驗證碼圖片路徑')
    parser.add_argument('--cdp', default='http://localhost:18792', help='Chrome CDP URL')
    parser.add_argument('--auto', action='store_true', help='自動從 EDMoms 頁面截圖然後解')
    args = parser.parse_args()

    if args.auto or not args.image:
        print("=" * 50)
        print("EDMoms 驗證碼破解器（自動截圖模式）")
        print("=" * 50)
        print(f"[1/2] 連接 Chrome CDP: {args.cdp}")
        img_path, page_url = capture_captcha_from_page(args.cdp)
        print(f"[2/2] 截圖完成: {img_path}")
        print(f"      頁面 URL: {page_url}")
    else:
        img_path = args.image

    if not os.path.exists(img_path):
        print(f"[錯誤] 圖片不存在: {img_path}")
        sys.exit(1)

    print(f"[3/3] 開始 OCR 辨識...")
    answer = solve_captcha(img_path)

    print("\n" + "=" * 50)
    print(f"🎯 驗證碼答案: {answer}")
    print("=" * 50)

    # 寫入結果檔（給自動化腳本讀取）
    lab_dir = Path('/Users/chung/.openclaw/workspace/Lab/2026-09-20-edmom-captcha-solver')
    lab_dir.mkdir(parents=True, exist_ok=True)
    result_file = lab_dir / 'captcha_result.txt'
    with open(result_file, 'w') as f:
        f.write(answer)
    print(f"📝 結果已寫入: {result_file}")

    return answer


if __name__ == '__main__':
    main()
