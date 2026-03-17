from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional
import json
import pandas as pd
from pathlib import Path
import shutil
import os

from timetable_renderer import TimetableRenderer
from compositor import Compositor
from palette_extractor_copy import PaletteExtractor 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

@app.post("/generate")
async def generate_timetable(
    schedule_data: str = Form(...),
    background_file: UploadFile = File(...),
    h_pos: str = Form("right"),
    v_pos: str = Form("top"),
    resolution: str = Form("fhd"),
    custom_width: Optional[int] = Form(None),
    custom_height: Optional[int] = Form(None)
):
    try:
        # 1. 배경 이미지 저장
        bg_path = OUTPUT_DIR / background_file.filename
        with open(bg_path, "wb") as buffer:
            shutil.copyfileobj(background_file.file, buffer)

        # 2. 색상 추출
        extractor = PaletteExtractor(str(bg_path))
        extractor.extract()

        # 3. 시간표 데이터 처리
        schedules = json.loads(schedule_data)

        # 🔧 FIX: 'name' → '강의명'
        filtered_schedules = [
            s for s in schedules if s.get("강의명", "").strip() != ""
        ]

        if not filtered_schedules:
            raise HTTPException(status_code=400, detail="강의 정보를 입력해주세요.")

        df = pd.DataFrame(filtered_schedules)

        # 🔧 FIX: 컬럼 순서 강제 지정
        df = df[["요일", "강의명", "시작", "종료", "강의실"]]

        csv_path = OUTPUT_DIR / "schedule.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 4. 시간표 렌더링
        renderer = TimetableRenderer(
            csv_path=str(csv_path),
            font_path="Cafe24Ssurround.woff",
            block_colors=extractor.block_colors,
            text_color=extractor.text_color,
            grid_color=extractor.grid_color
        )

        timetable_path = OUTPUT_DIR / "timetable_result.png"
        renderer.render(str(timetable_path))

        # 5. 배경 합성
        comp = Compositor(
            timetable_path=str(timetable_path),
            wallpaper_path=str(bg_path),
            h_pos=h_pos,
            v_pos=v_pos,
            resolution=resolution,
            custom_width=custom_width,
            custom_height=custom_height
        )

        final_path = OUTPUT_DIR / "final_wallpaper.png"
        comp.composite(str(final_path))

        return FileResponse(final_path, media_type="image/png")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
