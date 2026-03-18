from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from typing import Optional
import json
import pandas as pd
from pathlib import Path
import shutil
import os
import gc
import psutil
from datetime import datetime
from PIL import Image, ImageFile
import threading
import time

from timetable_renderer import TimetableRenderer
from compositor import Compositor
from palette_extractor_copy import PaletteExtractor

# ── 글로벌 메모리 모니터링 ──────────────────────────────────
memory_stats = {
    "current_mb": 0,
    "peak_mb": 0,
    "current_percent": 0,
    "timestamp": datetime.now().isoformat(),
}

def monitor_memory():
    """백그라운드 메모리 모니터링 스레드"""
    global memory_stats
    process = psutil.Process(os.getpid())
    
    while True:
        try:
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            
            memory_stats["current_mb"] = round(mem_mb, 1)
            memory_stats["current_percent"] = round(process.memory_percent(), 1)
            memory_stats["timestamp"] = datetime.now().isoformat()
            
            # 피크 메모리 업데이트
            if mem_mb > memory_stats["peak_mb"]:
                memory_stats["peak_mb"] = round(mem_mb, 1)
            
            time.sleep(0.5)  # 0.5초 간격 모니터링
        except:
            time.sleep(1)

# 백그라운드 스레드 시작
monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
monitor_thread.start() 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://wallpaper-timetable.pages.dev",
        "https://my-timetable-project.onrender.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

@app.get("/memory")
async def get_memory_stats():
    return JSONResponse({
        "timestamp": memory_stats["timestamp"],
        "memory_mb": memory_stats["current_mb"],
        "memory_percent": memory_stats["current_percent"],
        "peak_mb": memory_stats["peak_mb"],
        "limit_mb": 500,
        "usage_percent": round((memory_stats["current_mb"] / 500) * 100, 1)
    })

@app.get("/monitor", response_class=HTMLResponse)
async def monitor_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Backend Memory Monitor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                background-color: #f5f5f5;
                padding: 20px;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin: 30px 0;
            }
            .stat-box {
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #4CAF50;
            }
            .stat-label {
                color: #666;
                font-size: 14px;
                margin-bottom: 8px;
            }
            .stat-value {
                font-size: 28px;
                font-weight: bold;
                color: #333;
            }
            .progress-bar {
                width: 100%;
                height: 25px;
                background-color: #ddd;
                border-radius: 5px;
                overflow: hidden;
                margin-top: 10px;
            }
            .progress-fill {
                height: 100%;
                background-color: #4CAF50;
                text-align: center;
                color: white;
                font-size: 12px;
                line-height: 25px;
                transition: width 0.3s ease;
            }
            .progress-fill.warning {
                background-color: #ff9800;
            }
            .progress-fill.danger {
                background-color: #f44336;
            }
            .timestamp {
                text-align: center;
                color: #999;
                font-size: 12px;
                margin-top: 20px;
            }
            .refresh-info {
                text-align: center;
                color: #666;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Backend Memory Monitor</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-label">Current Memory</div>
                    <div class="stat-value" id="memory-mb">-</div>
                    <div class="stat-label">MB</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">Peak Memory</div>
                    <div class="stat-value" id="peak-mb">-</div>
                    <div class="stat-label">MB (this session)</div>
                </div>

                <div class="stat-box">
                    <div class="stat-label">Usage %</div>
                    <div class="stat-value" id="usage-percent">-</div>
                    <div class="stat-label">of 500MB limit</div>
                </div>

                <div class="stat-box">
                    <div class="stat-label">Status</div>
                    <div class="stat-value" id="status">-</div>
                    <div class="stat-label" id="status-msg">-</div>
                </div>
            </div>
            
            <div class="stat-box" style="grid-column: 1 / -1;">
                <div class="stat-label">Memory Usage Bar</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%">0%</div>
                </div>
            </div>
            
            <div class="refresh-info">
                Status: Real-time monitoring (0.1s update)
            </div>
            
            <div class="timestamp" id="timestamp">-</div>
        </div>
        
        <script>
            async function updateMemory() {
                try {
                    const response = await fetch('/memory');
                    const data = await response.json();
                    
                    document.getElementById('memory-mb').textContent = data.memory_mb;
                    document.getElementById('peak-mb').textContent = data.peak_mb;
                    document.getElementById('usage-percent').textContent = data.usage_percent;
                    document.getElementById('timestamp').textContent = 'Last updated: ' + new Date(data.timestamp).toLocaleTimeString();
                    
                    // 상태 표시
                    const statusEl = document.getElementById('status');
                    const statusMsg = document.getElementById('status-msg');
                    if (data.usage_percent > 80) {
                        statusEl.textContent = '⚠️ CRITICAL';
                        statusEl.style.color = '#f44336';
                        statusMsg.textContent = 'Memory usage critically high';
                    } else if (data.usage_percent > 60) {
                        statusEl.textContent = '⚡ WARNING';
                        statusEl.style.color = '#ff9800';
                        statusMsg.textContent = 'Memory usage elevated';
                    } else {
                        statusEl.textContent = '✅ OK';
                        statusEl.style.color = '#4CAF50';
                        statusMsg.textContent = 'Memory usage normal';
                    }
                    
                    const progressFill = document.getElementById('progress-fill');
                    const percentage = data.usage_percent;
                    progressFill.style.width = percentage + '%';
                    progressFill.textContent = Math.round(percentage) + '%';
                    
                    progressFill.classList.remove('warning', 'danger');
                    if (percentage > 80) {
                        progressFill.classList.add('danger');
                    } else if (percentage > 60) {
                        progressFill.classList.add('warning');
                    }
                } catch (error) {
                    console.error('Error fetching memory stats:', error);
                }
            }
            
            updateMemory();
            setInterval(updateMemory, 100);
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/generate")
async def generate_timetable(
    schedule_data: str = Form(...),
    background_file: UploadFile = File(...),
    h_pos: str = Form("right"),
    v_pos: str = Form("top"),
    resolution: str = Form("fhd"),
    size_ratio: float = Form(0.78),
    custom_width: Optional[int] = Form(None),
    custom_height: Optional[int] = Form(None)
):
    temp_files = []
    process = psutil.Process(os.getpid())
    
    def log_memory(stage: str):
        """각 단계별 메모리 사용량 로깅"""
        mem_mb = process.memory_info().rss / (1024 * 1024)
        print(f"[MEMORY] {stage}: {round(mem_mb, 1)} MB ({round((mem_mb/500)*100, 1)}%)")
    
    try:
        # 1. 배경 이미지 저장
        log_memory("START")
        bg_path = OUTPUT_DIR / background_file.filename
        with open(bg_path, "wb") as buffer:
            shutil.copyfileobj(background_file.file, buffer)
        temp_files.append(bg_path)
        log_memory("After saving background")

        # 2. 색상 추출
        extractor = PaletteExtractor(str(bg_path))
        extractor.extract()
        log_memory("After palette extraction")

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
        temp_files.append(csv_path)
        log_memory("After CSV creation")

        # 4. 시간표 렌더링
        renderer = TimetableRenderer(
            csv_path=str(csv_path),
            font_path="Cafe24Ssurround.woff",
            block_colors=extractor.block_colors,
            text_color=extractor.text_color,
            grid_color=extractor.grid_color,
            scale=2  # 크기 균형: 1(작음) → 2(중간) → 4(원본)
        )

        timetable_path = OUTPUT_DIR / "timetable_result.png"
        renderer.render(str(timetable_path))
        temp_files.append(timetable_path)
        log_memory("After timetable rendering")

        # 5. 배경 합성
        comp = Compositor(
            timetable_path=str(timetable_path),
            wallpaper_path=str(bg_path),
            size_ratio=size_ratio,
            h_pos=h_pos,
            v_pos=v_pos,
            resolution=resolution,
            custom_width=custom_width,
            custom_height=custom_height
        
        )

        final_path = OUTPUT_DIR / "final_wallpaper.png"
        final_image = comp.composite(str(final_path))
        log_memory("After compositing")

        # ── 정상 응답 ──────────────────────────────────────────
        return FileResponse(final_path, media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        log_memory("FINALLY (cleanup start)")
        # ── 메모리 & 임시 파일 정리 (aggressive cleanup) ──────────────────
        # 1. 변수들 정리
        if 'extractor' in locals():
            del extractor
        if 'renderer' in locals():
            del renderer
        if 'comp' in locals():
            del comp
        if 'df' in locals():
            del df
        
        # 2. 파일 스트림 정리
        try:
            background_file.file.close()
        except:
            pass
        
        # 3. 임시 파일 정리 (최종 파일 제외)
        for temp_file in temp_files:
            try:
                if temp_file.exists() and temp_file.name != "final_wallpaper.png":
                    temp_file.unlink()
            except Exception:
                pass
        
        # 4. PIL 이미지 캐시 정리 (중요: 메모리 누수 방지)
        try:
            Image._clear_cache()
        except AttributeError:
            # PIL 버전에 따라 _clear_cache()가 없을 수 있음
            pass
        
        # 5. 강제 가비지 컬렉션
        gc.collect()
        log_memory("FINALLY (cleanup end)")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"  # Render에서 모든 인터페이스에서 수신 필요
    uvicorn.run(app, host=host, port=port)
