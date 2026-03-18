# timetable_renderer.py
import csv
import re
import gc
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ── 상수 ─────────────────────────────────────────────────────────────
DAYS          = ["월", "화", "수", "목", "금"]
REQUIRED_COLS = {"요일", "강의명", "시작", "종료", "강의실"}
TIME_RE       = re.compile(r"^\d{2}:\d{2}$")


class TimetableRenderer:

    def __init__(
        self,
        csv_path:     str   = "schedule.csv",
        font_path:    str   = "Cafe24Ssurround.woff",
        block_colors: list  = None,
        text_color:   tuple = (255, 255, 255),
        grid_color:   tuple = (180, 180, 180, 60),
        scale:        int   = 2,
    ):
        self.csv_path     = csv_path
        self.font_path    = font_path
        self.block_colors = block_colors or [
            (100, 181, 246, 200), ( 41, 182, 246, 200),
            ( 30, 136, 229, 200), ( 21,  99, 194, 200),
            ( 13,  71, 161, 200), ( 92, 107, 192, 200),
        ]
        self.text_color = text_color
        self.grid_color = grid_color
        self.scale      = scale
        self.courses    = []

    # ── 1. 입력 검증 ─────────────────────────────────────────────
    def _validate(self):
        # 폰트 파일 확인
        if not Path(self.font_path).exists():
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없어요: {self.font_path}")

        # CSV 파일 확인
        if not Path(self.csv_path).exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없어요: {self.csv_path}")

        with open(self.csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows   = list(reader)

        # 컬럼 확인
        if not rows:
            raise ValueError("CSV 파일이 비어있어요.")
        missing = REQUIRED_COLS - set(rows[0].keys())
        if missing:
            raise ValueError(f"CSV에 필수 컬럼이 없어요: {missing}")

        # 각 행 검증
        courses = []
        for i, row in enumerate(rows, start=2):
            line  = f"CSV {i}행"
            name  = row["강의명"].strip()
            day   = row["요일"].strip()
            start = row["시작"].strip()
            end   = row["종료"].strip()

            if not name:
                raise ValueError(f"{line}: 강의명이 비어있어요.")
            if day not in DAYS:
                raise ValueError(f"{line}: 요일 값이 올바르지 않아요 → '{day}'")
            if not TIME_RE.match(start):
                raise ValueError(f"{line}: 시작 시간 형식이 올바르지 않아요 → '{start}'")
            if not TIME_RE.match(end):
                raise ValueError(f"{line}: 종료 시간 형식이 올바르지 않아요 → '{end}'")

            sh, sm    = map(int, start.split(":"))
            eh, em    = map(int, end.split(":"))
            start_min = sh * 60 + sm
            end_min   = eh * 60 + em
            if start_min >= end_min:
                raise ValueError(f"{line}: 시작 시간이 종료 시간보다 늦거나 같아요 → {start} ~ {end}")

            courses.append({
                "day":   day,
                "name":  name,
                "start": start_min,
                "end":   end_min,
                "room":  row["강의실"].strip(),
            })

        return courses

    # ── 2. 시간 범위 자동 계산 ───────────────────────────────────
    def _calc_time_range(self, courses):
        """가장 이른 시작 정각 ~ 가장 늦은 종료 정각"""
        min_start  = min(c["start"] for c in courses)
        max_end    = max(c["end"]   for c in courses)
        time_start = (min_start // 60) * 60         # 내림
        time_end   = ((max_end + 59) // 60) * 60    # 올림
        return time_start, time_end

    # ── 3. 폰트 크기 자동 계산 ───────────────────────────────────
    # 수정됨: 기준을 5글자에서 6글자("가나다라마바")로 변경하여 폰트 크기를 줄임
    def _calc_font_size(self, draw, bw, ref="가나다라마바"):
        """블록 너비에 6글자가 꽉 차는 폰트 크기 탐색"""
        fs = 6
        while True:
            f = ImageFont.truetype(self.font_path, (fs + 1) * self.scale)
            b = draw.textbbox((0, 0), ref, font=f)
            if b[2] - b[0] > bw:
                break
            fs += 1
        return ImageFont.truetype(self.font_path, fs * self.scale)

    # ── 4. 블록 내 텍스트 렌더링 ────────────────────────────────
    def _draw_text_in_block(self, draw, lines, font, font_room, x0, y0, x1, y1, pad):
        """강의명 줄바꿈 + 강의실 텍스트를 블록 중앙에 배치"""
        bw = x1 - x0 - pad * 2
        bh = y1 - y0 - pad * 2

        lh       = draw.textbbox((0, 0), "가", font=font)[3] - draw.textbbox((0, 0), "가", font=font)[1]
        line_gap = int(lh * 0.2)
        name_h   = lh * len(lines) + line_gap * (len(lines) - 1)

        rlh      = draw.textbbox((0, 0), "가", font=font_room)[3] - draw.textbbox((0, 0), "가", font=font_room)[1]
        room_gap = int(rlh * 0.15)
        between  = int(lh * 0.25)
        room_h   = rlh * 2 + room_gap
        total_h  = name_h + between + room_h

        # 블록이 충분히 높을 때만 강의실 표시
        show_room  = bh >= total_h + pad
        draw_h     = total_h if show_room else name_h
        top_offset = draw.textbbox((0, 0), lines[0], font=font)[1]
        ty         = y0 + pad + (bh - draw_h) // 2 - top_offset

        for line in lines:
            tw = draw.textbbox((0, 0), line, font=font)[2]
            tx = x0 + pad + (bw - tw) // 2
            draw.text((tx, ty), line, font=font, fill=(*self.text_color, 245))
            ty += lh + line_gap

        return ty, show_room, rlh, room_gap, between

    # ── 5. 전체 렌더링 ───────────────────────────────────────────
    def render(self, output_path: str = "timetable.png"):
        S = self.scale

        print("입력 검증 중...")
        self.courses = self._validate()
        print(f"  → {len(self.courses)}개 강의 확인 완료")

        # 시간 범위 계산
        time_start, time_end = self._calc_time_range(self.courses)
        total_min = time_end - time_start
        N_HOURS   = total_min // 60
        print(f"  → 시간 범위: {time_start//60:02d}:00 ~ {time_end//60:02d}:00")

        # 레이아웃 상수
        COL_TIME_W   = 70  * S
        COL_DAY_W    = 130 * S
        ROW_HEADER_H = 45  * S
        BOTTOM_PAD   = 10  * S
        PAD          = 4   * S
        RADIUS       = 6   * S
        SHADOW_OFF   = 4   * S
        SHADOW_BLUR  = 6   * S

        # 목표 높이 기준으로 분당 픽셀 계산
        TARGET_H = 3820
        MIN_H    = (TARGET_H - ROW_HEADER_H - BOTTOM_PAD) / total_min

        TOTAL_W = COL_TIME_W + COL_DAY_W * len(DAYS)
        TOTAL_H = TARGET_H

        # 과목별 색상 매핑 (같은 과목 = 같은 색)
        unique_names = list(dict.fromkeys(c["name"] for c in self.courses))
        color_map    = {
            name: self.block_colors[i % len(self.block_colors)]
            for i, name in enumerate(unique_names)
        }

        # 그림자 레이어 / 블록 레이어 분리
        shadow_layer = Image.new("RGBA", (TOTAL_W, TOTAL_H), (0, 0, 0, 0))
        block_layer  = Image.new("RGBA", (TOTAL_W, TOTAL_H), (0, 0, 0, 0))
        draw_sh      = ImageDraw.Draw(shadow_layer)
        draw_bl      = ImageDraw.Draw(block_layer)

        # 폰트
        font_time = ImageFont.truetype(self.font_path, 12  * S)
        font_day  = ImageFont.truetype(self.font_path, 14 * S)
        font_room = ImageFont.truetype(self.font_path, 11 * S)

        # 그리드선 색 (정시 / 30분 구분)
        gc   = self.grid_color
        gc_h = (*gc[:3], gc[3] // 2)

        # 수직선 (요일 경계)
        for i in range(len(DAYS) + 1):
            x = COL_TIME_W + COL_DAY_W * i
            draw_bl.line([(x, 0), (x, TOTAL_H)], fill=gc, width=max(1, S // 2))

        # 수평선 (시간 경계)
        for h in range(N_HOURS + 1):
            y = ROW_HEADER_H + int(h * 60 * MIN_H)
            draw_bl.line([(0, y), (TOTAL_W, y)], fill=gc, width=max(1, S // 2))
            if h < N_HOURS:
                # 30분 선 (더 연하게)
                y_half = ROW_HEADER_H + int((h * 60 + 30) * MIN_H)
                draw_bl.line([(COL_TIME_W, y_half), (TOTAL_W, y_half)],
                             fill=gc_h, width=max(1, S // 2))

        # 요일 헤더
        for i, day in enumerate(DAYS):
            x    = COL_TIME_W + COL_DAY_W * i + COL_DAY_W // 2
            y    = ROW_HEADER_H // 2
            bbox = draw_bl.textbbox((0, 0), day, font=font_day)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw_bl.text((x - tw//2, y - th//2), day,
                         font=font_day, fill=(*self.text_color, 255))

        # 시간 레이블 (정시마다)
        for h in range(N_HOURS + 1):
            hour  = time_start // 60 + h
            label = f"{hour:02d}:00"
            y     = ROW_HEADER_H + int(h * 60 * MIN_H)
            bbox  = draw_bl.textbbox((0, 0), label, font=font_time)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw_bl.text((COL_TIME_W - tw - 6*S, y - th//2 + 2),
                         label, font=font_time, fill=(*self.text_color, 255))

        # 수업 블록 렌더링
        day_idx = {d: i for i, d in enumerate(DAYS)}

        print("렌더링 중...")
        for c in self.courses:
            di = day_idx[c["day"]]
            x0 = COL_TIME_W + COL_DAY_W * di + PAD
            x1 = COL_TIME_W + COL_DAY_W * (di + 1) - PAD
            y0 = ROW_HEADER_H + int((c["start"] - time_start) * MIN_H) + PAD
            y1 = ROW_HEADER_H + int((c["end"]   - time_start) * MIN_H) - PAD
            col = color_map[c["name"]]

            # 블록 그림자 (별도 레이어에 오프셋 후 가우시안 블러)
            draw_sh.rounded_rectangle(
                [x0+SHADOW_OFF, y0+SHADOW_OFF, x1+SHADOW_OFF, y1+SHADOW_OFF],
                radius=RADIUS, fill=(0, 0, 0, 140)
            )

            # 블록 본체
            draw_bl.rounded_rectangle([x0, y0, x1, y1], radius=RADIUS, fill=col)
            border = tuple(min(255, v+40) if i < 3 else 220 for i, v in enumerate(col))
            draw_bl.rounded_rectangle([x0, y0, x1, y1], radius=RADIUS,
                                      outline=border, width=S)

            # --- 이 부분만 수정되었습니다: 6자 기준 폰트 및 띄어쓰기 유지 줄바꿈 ---
            bw = x1 - x0 - PAD * 2
            font_course = self._calc_font_size(draw_bl, bw) # 내부적으로 "가나다라마바" 기준 사용
            name_words = c["name"].split()
            lines, cur = [], ""
            for word in name_words:
                test = cur + " " + word if cur else word
                # 띄어쓰기로 합쳤을 때 너비가 넘어가면 줄바꿈
                if draw_bl.textbbox((0, 0), test, font=font_course)[2] > bw:
                    if cur: lines.append(cur)
                    cur = word
                    # 만약 단어 자체가 6글자보다 길어서 한 줄을 넘어가면 글자 단위로 강제 줄바꿈
                    while draw_bl.textbbox((0, 0), cur, font=font_course)[2] > bw:
                        for i in range(1, len(cur) + 1):
                            if draw_bl.textbbox((0, 0), cur[:i], font=font_course)[2] > bw:
                                lines.append(cur[:i-1])
                                cur = cur[i-1:]
                                break
                else:
                    cur = test
            if cur: lines.append(cur)
            # -------------------------------------------------------------------

            # 강의명 + 강의실 렌더링
            ty, show_room, rlh, room_gap, between = self._draw_text_in_block(
                draw_bl, lines, font_course, font_room, x0, y0, x1, y1, PAD
            )

            # 강의실 (블록 높이가 충분할 때만 표시)
            if show_room and c["room"]:
                ty += between
                # 강의실 텍스트 줄바꿈
                room_words   = c["room"].split()
                room_display = []
                buf          = ""
                for word in room_words:
                    test = buf + " " + word if buf else word
                    if draw_bl.textbbox((0, 0), test, font=font_room)[2] > bw and buf:
                        room_display.append(buf)
                        buf = word
                    else:
                        buf = test
                if buf:
                    room_display.append(buf)

                r_top = draw_bl.textbbox((0, 0), room_display[0], font=font_room)[1]
                ty   -= r_top
                for rline in room_display[:2]:   # 최대 2줄
                    rtw = draw_bl.textbbox((0, 0), rline, font=font_room)[2]
                    rtx = x0 + PAD + (bw - rtw) // 2
                    draw_bl.text((rtx, ty), rline, font=font_room,
                                 fill=(*self.text_color, 210))
                    ty += rlh + room_gap

        # 그림자 블러 처리 후 레이어 합성
        shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))
        img = Image.new("RGBA", (TOTAL_W, TOTAL_H), (0, 0, 0, 0))
        img.paste(shadow_blurred, (0, 0), shadow_blurred)
        img.paste(block_layer,    (0, 0), block_layer)

        img.save(output_path)
        print(f"  → {output_path} 저장 완료! ({TOTAL_W}x{TOTAL_H})")
        
        # ── 메모리 정리 ───────────────────────────────────────────
        # 대용량 이미지 레이어 명시적 해제 (메모리 누수 방지)
        if hasattr(shadow_layer, 'close'):
            shadow_layer.close()
        if hasattr(block_layer, 'close'):
            block_layer.close()
        if hasattr(shadow_blurred, 'close'):
            shadow_blurred.close()
        if hasattr(img, 'close'):
            img.close()
        
        return output_path


if __name__ == "__main__":
    import json

    # palette.json 에서 색상 로드
    palette_path = Path("output/palette.json")
    if palette_path.exists():
        with open(palette_path) as f:
            palette = json.load(f)
        block_colors = [tuple(c) for c in palette["block_colors"]]
        text_color   = tuple(palette["text_color"])
        grid_color   = tuple(palette["grid_color"])
        print("팔레트 로드 완료: output/palette.json")
    else:
        # palette.json 없으면 기본 파란색 팔레트 사용
        block_colors = None
        text_color   = (255, 255, 255)
        grid_color   = (180, 180, 180, 60)
        print("⚠️  palette.json 없음 → 기본 팔레트 사용")

    renderer = TimetableRenderer(
        csv_path     = "output/schedule.csv",
        font_path    = "Cafe24Ssurround.woff",
        block_colors = block_colors,
        text_color   = text_color,
        grid_color   = grid_color,
    )
    renderer.render("output/timetable.png")
