# compositor.py
from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil
import gc

import numpy as np
from PIL import Image, ImageFilter


# 지원 해상도
RESOLUTIONS = {
    "fhd":      (1920, 1080),
    "qhd":      (2560, 1440),
    "original": None,           # 원본 크기 유지
}

MAX_CUSTOM_WIDTH = 3840
MAX_CUSTOM_HEIGHT = 2160


H_POS = ["left", "center", "right"]
V_POS = ["top",  "center", "bottom"]


class Compositor:

    def __init__(
        self,
        timetable_path: str   = "timetable.png",
        wallpaper_path: str   = "wallpaper.png",
        size_ratio:     float = 0.78,       # 배경 세로 기준 시간표 크기 비율
        h_pos:          str   = "right",    # 수평 위치: left / center / right
        v_pos:          str   = "top",      # 수직 위치: top / center / bottom
        resolution:     str   = "fhd",      # 출력 해상도: fhd / qhd / original / custom
        custom_width:   Optional[int] = None,  # custom ??(px)
        custom_height:  Optional[int] = None,  # custom ??(px)
        padding:        int   = 40,         # 가장자리 여백 px
        shadow:         bool  = True,       # 전체 시간표 그림자 켜기/끄기
    ):
        self.timetable_path = timetable_path
        self.wallpaper_path = wallpaper_path
        self.size_ratio     = size_ratio
        self.h_pos          = h_pos.lower()
        self.v_pos          = v_pos.lower()
        self.resolution     = resolution.lower()
        self.custom_width   = custom_width
        self.custom_height  = custom_height
        self.padding        = padding
        self.shadow         = shadow

    # ── 1. 입력 검증 ─────────────────────────────────────────────
    def _validate(self):
        if not Path(self.timetable_path).exists():
            raise FileNotFoundError(f"시간표 파일을 찾을 수 없어요: {self.timetable_path}")
        if not Path(self.wallpaper_path).exists():
            raise FileNotFoundError(f"배경화면 파일을 찾을 수 없어요: {self.wallpaper_path}")
        if not (0.1 <= self.size_ratio <= 1.0):
            raise ValueError(f"크기 비율은 0.1 ~ 1.0 사이여야 해요: {self.size_ratio}")
        if self.h_pos not in H_POS:
            raise ValueError(f"수평 위치는 {H_POS} 중 하나여야 해요: {self.h_pos}")
        if self.v_pos not in V_POS:
            raise ValueError(f"수직 위치는 {V_POS} 중 하나여야 해요: {self.v_pos}")
        if self.custom_width is not None or self.custom_height is not None:
            if self.custom_width is None or self.custom_height is None:
                raise ValueError("custom ???? ??/??? ?? ???? ??.")
            if self.custom_width <= 0 or self.custom_height <= 0:
                raise ValueError("custom ???? 0?? ? ???? ??.")
            if self.custom_width > MAX_CUSTOM_WIDTH or self.custom_height > MAX_CUSTOM_HEIGHT:
                raise ValueError(
                    f"custom ???? ?? {MAX_CUSTOM_WIDTH}x{MAX_CUSTOM_HEIGHT}?? ??? ? ???."
                )
        else:
            if self.resolution not in RESOLUTIONS:
                raise ValueError(f"해상도는 {list(RESOLUTIONS.keys())} 중 하나여야 해요: {self.resolution}")

    # ── 2. 배경화면 준비 (리사이즈 + 센터 크롭) ──────────────────
    def _prepare_bg(self):
        bg = Image.open(self.wallpaper_path).convert("RGBA")

        # 메모리 절감: 너무 큰 이미지는 먼저 다운스케일링 (최대 QHD)
        if bg.width > 2560 or bg.height > 1440:
            scale_factor = min(2560 / bg.width, 1440 / bg.height)
            bg = bg.resize((int(bg.width * scale_factor), int(bg.height * scale_factor)), Image.LANCZOS)

        if self.custom_width is not None and self.custom_height is not None:
            target = (self.custom_width, self.custom_height)
        else:
            target = RESOLUTIONS[self.resolution]
        if target is None:
            return bg   # 원본 유지

        tw, th = target
        bw, bh = bg.size
        scale  = max(tw / bw, th / bh)
        bg_r   = bg.resize((int(bw * scale), int(bh * scale)), Image.LANCZOS)
        left   = (bg_r.width  - tw) // 2
        top    = (bg_r.height - th) // 2
        return bg_r.crop((left, top, left + tw, top + th))

    # ── 3. 시간표 리사이즈 ───────────────────────────────────────
    def _prepare_tt(self, bg_h):
        """배경 세로 기준 size_ratio 비율로 시간표 리사이즈"""
        tt   = Image.open(self.timetable_path)   # RGBA
        tt_h = int(bg_h * self.size_ratio)
        tt_w = int(tt.size[0] * (tt_h / tt.size[1]))
        return tt.resize((tt_w, tt_h), Image.LANCZOS)

    # ── 4. 배치 위치 계산 ────────────────────────────────────────
    def _calc_pos(self, bg_w, bg_h, tt_w, tt_h):
        pad = self.padding

        # 수평 위치
        if self.h_pos == "left":
            pos_x = pad
        elif self.h_pos == "center":
            pos_x = (bg_w - tt_w) // 2
        else:   # right
            pos_x = bg_w - tt_w - pad

        # 수직 위치
        if self.v_pos == "top":
            pos_y = pad
        elif self.v_pos == "center":
            pos_y = (bg_h - tt_h) // 2
        else:   # bottom
            pos_y = bg_h - tt_h - pad

        return pos_x, pos_y

    # ── 5. 전체 시간표 그림자 생성 ───────────────────────────────
    def _make_shadow(self, tt):
        """시간표 알파 채널 기반 드롭 섀도우"""
        sh_arr = np.array(tt).copy()
        sh_arr[:, :, :3] = [0, 0, 0]
        sh_arr[:, :,  3] = (sh_arr[:, :, 3].astype(float) * 0.45).astype(np.uint8)
        return Image.fromarray(sh_arr, "RGBA").filter(ImageFilter.GaussianBlur(18))

    # ── 6. 합성 & 저장 ───────────────────────────────────────────
    def composite(self, output_path: str = "output/output.png"):
        print("입력 검증 중...")
        self._validate()

        print("배경화면 준비 중...")
        bg         = self._prepare_bg()
        bg_w, bg_h = bg.size
        print(f"  → 배경 크기: {bg_w}x{bg_h}")

        print("시간표 준비 중...")
        tt         = self._prepare_tt(bg_h)
        tt_w, tt_h = tt.size
        print(f"  → 시간표 크기: {tt_w}x{tt_h}")

        pos_x, pos_y = self._calc_pos(bg_w, bg_h, tt_w, tt_h)
        print(f"  → 배치 위치: ({pos_x}, {pos_y})  [{self.h_pos} / {self.v_pos}]")

        comp = bg.copy()

        # 그림자 합성
        if self.shadow:
            shadow = self._make_shadow(tt)
            comp.paste(shadow, (pos_x + 8, pos_y + 10), shadow)

        # 시간표 합성
        comp.paste(tt, (pos_x, pos_y), tt)

        # output 폴더에 저장
        comp.convert("RGB").save(output_path, quality=97)
        print(f"  → {output_path} 저장 완료!")

        # ── 아카이브 저장 (개발 환경에서만) ─────────────────────────────────────────
        # 프로덕션에서는 비활성화 (디스크 I/O 성능 최적화)
        # archive_dir  = Path("archive")
        # archive_dir.mkdir(exist_ok=True)
        # timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        # archive_path = archive_dir / f"output_{timestamp}.png"
        # shutil.copy2(output_path, archive_path)
        # print(f"  → 아카이브 저장: {archive_path}")

        # ── 메모리 정리 ───────────────────────────────────────────
        # 대용량 이미지 객체 명시적 해제 (메모리 누수 방지)
        if hasattr(bg, 'close'):
            bg.close()
        if hasattr(tt, 'close'):
            tt.close()
        if hasattr(comp, 'close'):
            comp.close()
        if 'shadow' in locals() and hasattr(shadow, 'close'):
            shadow.close()

        return output_path


if __name__ == "__main__":
    comp = Compositor(
        timetable_path = "output/timetable.png",
        wallpaper_path = "wallpaper.png",
        size_ratio     = 0.75,
        h_pos          = "right",
        v_pos          = "top",
        resolution     = "qhd",
        padding        = 40,
        shadow         = True,
    )
    comp.composite("output/output.png")