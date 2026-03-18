# palette_extractor.py
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from sklearn.cluster import KMeans
import gc
import colorsys


class PaletteExtractor:

    def __init__(self, image_path: str, n_colors: int = 8, sample_rate: int = 30):
        self.image_path   = image_path
        self.n_colors     = n_colors
        self.sample_rate  = sample_rate  # 픽셀 샘플링 비율 (30 = 1/30만 사용)
        self.block_colors = []
        self.text_color   = None
        self.grid_color   = None

    # ── 1. 색상 추출 ──────────────────────────────────────────────
    def extract(self):
        # 이미지 로드
        img    = Image.open(self.image_path).convert("RGB")
        
        # 메모리 절감: 너무 큰 이미지는 먼저 다운스케일링
        if img.width > 1920 or img.height > 1440:
            scale_factor = min(1920 / img.width, 1440 / img.height)
            img = img.resize((int(img.width * scale_factor), int(img.height * scale_factor)), Image.LANCZOS)
        
        arr    = np.array(img)
        pixels = arr.reshape(-1, 3).astype(float)

        # 너무 밝거나 어두운 픽셀 제외 (순수 그림자/하이라이트 제거)
        brightness = pixels.mean(axis=1)
        mid        = pixels[(brightness > 30) & (brightness < 225)]

        # 픽셀 샘플링으로 속도 개선
        mid = mid[::self.sample_rate]

        # K-Means로 대표 색상 추출 (파라미터 최적화)
        km = KMeans(
            n_clusters = self.n_colors,
            random_state = 42,
            n_init       = 3,
            max_iter     = 100,
            algorithm    = "lloyd",
        )
        km.fit(mid)
        centers = km.cluster_centers_
        counts  = np.bincount(km.labels_)
        order   = np.argsort(-counts)   # 비중 높은 순 정렬

        # 블록용 색상: 채도 강화 + 명도 약간 낮춤 (배경에 묻히지 않게)
        self.block_colors = []
        for i in order:
            r, g, b = centers[i]
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            s = min(s * 1.2, 1.0)
            v = min(max(v, 0.55), 0.80)
            nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
            self.block_colors.append(
                (int(nr*255), int(ng*255), int(nb*255), 200)
            )

        # 글자색: 배경 평균 밝기 기준으로 흰색/어두운색 선택
        avg_brightness  = pixels.mean()
        self.text_color = (255, 255, 255) if avg_brightness < 128 else (30, 30, 30)

        # 그리드색: 가장 비중 높은 색 기반, 반투명
        dominant        = centers[order[0]]
        self.grid_color = (
            int(dominant[0]), int(dominant[1]), int(dominant[2]), 40
        )

        # ── 메모리 정리 ───────────────────────────────────────────
        # 대용량 NumPy 배열 명시적 해제 (메모리 누수 방지)
        del arr, pixels, mid, km
        if hasattr(img, 'close'):
            img.close()

        return self

    # ── 2. 결과 출력 ──────────────────────────────────────────────
    def print_result(self):
        print("=== 블록 색상 ===")
        for i, c in enumerate(self.block_colors):
            print(f"  {i+1}. RGB{c[:3]}  #{c[0]:02X}{c[1]:02X}{c[2]:02X}")
        print(f"\n글자색:  RGB{self.text_color}")
        print(f"그리드:  RGB{self.grid_color}")

    # ── 3. 팔레트 스워치 이미지 저장 ─────────────────────────────
    def save_swatch(self, output_path: str = "palette_output.png"):
        SWATCH_W, SWATCH_H = 160, 60
        COLS, ROWS = 4, 2
        PAD   = 10
        IMG_W = COLS * (SWATCH_W + PAD) + PAD
        IMG_H = ROWS * (SWATCH_H + PAD) + PAD + 50

        # 한글 폰트 설정
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 14)
        except:
            font = ImageFont.load_default()

        vis  = Image.new("RGB", (IMG_W, IMG_H), (240, 240, 240))
        draw = ImageDraw.Draw(vis)

        for idx, col in enumerate(self.block_colors):
            row = idx // COLS
            c   = idx  % COLS
            x0  = PAD + c * (SWATCH_W + PAD)
            y0  = PAD + row * (SWATCH_H + PAD)
            draw.rectangle([x0, y0, x0+SWATCH_W, y0+SWATCH_H], fill=col[:3])
            draw.text((x0+4, y0+SWATCH_H-18),
                      f"#{col[0]:02X}{col[1]:02X}{col[2]:02X}",
                      fill=(255, 255, 255), font=font)

        draw.text((PAD, IMG_H-40), f"글자색: RGB{self.text_color}",
                  fill=(0, 0, 0), font=font)
        draw.text((PAD, IMG_H-20), f"그리드: RGB{self.grid_color}",
                  fill=(0, 0, 0), font=font)

        vis.save(output_path)
        print(f"팔레트 저장 완료: {output_path}")
        return output_path

    def save_json(self, output_path: str = "output/palette.json"):
        import json
        data = {
            "block_colors": [list(c) for c in self.block_colors],
            "text_color":   list(self.text_color),
            "grid_color":   list(self.grid_color),
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"팔레트 JSON 저장 완료: {output_path}")

if __name__ == "__main__":
    extractor = PaletteExtractor("wallpaper.png", n_colors=8, sample_rate=10)
    extractor.extract()
    extractor.print_result()
    extractor.save_swatch("output/palette_output.png")
    extractor.save_json("output/palette.json")