import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const MAX_CUSTOM_WIDTH = 3840;
  const MAX_CUSTOM_HEIGHT = 2160;

  const [schedules, setSchedules] = useState([
    { day: "월", name: "디지털 논리회로", startH: "09", startM: "00", endH: "10", endM: "00", room: "" },
    { day: "월", name: "데이터통신", startH: "10", startM: "00", endH: "12", endM: "00", room: "Y5428" },
    { day: "월", name: "신호및시스템", startH: "14", startM: "00", endH: "15", endM: "00", room: "Y5428" },
    { day: "화", name: "채플", startH: "12", startM: "00", endH: "13", endM: "00", room: "Y22217" },
    { day: "화", name: "통합적커뮤니케이션", startH: "15", startM: "00", endH: "17", endM: "30", room: "Y9001" },
    { day: "수", name: "디지털 논리회로", startH: "09", startM: "00", endH: "11", endM: "00", room: "Y5425" },
    { day: "수", name: "데이터통신", startH: "11", startM: "00", endH: "12", endM: "00", room: "Y5428" },
    { day: "수", name: "신호및시스템", startH: "13", startM: "00", endH: "15", endM: "00", room: "Y5428" },
    { day: "수", name: "인공지능수학", startH: "16", startM: "00", endH: "18", endM: "00", room: "Y5434" },
    { day: "목", name: "미학의이해", startH: "13", startM: "00", endH: "15", endM: "00", room: "Y9001" },
  ]);
  const [bgFile, setBgFile] = useState(null);
  const [bgFileName, setBgFileName] = useState(null);
  const [hPos, setHPos] = useState("right");
  const [vPos, setVPos] = useState("top");
  const [res, setRes] = useState("fhd");
  const [customWidth, setCustomWidth] = useState("1920");
  const [customHeight, setCustomHeight] = useState("1080");
  const [sizePercent, setSizePercent] = useState("78");
  const [textColor, setTextColor] = useState("white");
  const [resultImage, setResultImage] = useState(null);
  const [loading, setLoading] = useState(false);

  const days = ["월", "화", "수", "목", "금"];
  const hours = Array.from({ length: 16 }, (_, i) => String(i + 7).padStart(2, "0"));
  const minutes = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0"));
  const apiBase = (import.meta.env.VITE_API_BASE_URL || "https://my-timetable-project.onrender.com").replace(/\/$/, "");

  const generateTimetable = async () => {
    if (!bgFile) return alert("배경화면 이미지를 업로드해 주세요.");
    
    // 이전 결과 이미지와 메시지 지우기
    setResultImage(null);
    setLoading(true);

    try {
      const formattedSchedules = schedules.map((s) => ({
        "요일": s.day,
        "강의명": s.name || "미정",
        "시작": `${s.startH}:${s.startM}`,
        "종료": `${s.endH}:${s.endM}`,
        "강의실": s.room || "장소미정",
      }));

      const formData = new FormData();
      formData.append("schedule_data", JSON.stringify(formattedSchedules));
      formData.append("background_file", bgFile);
      formData.append("h_pos", hPos);
      formData.append("v_pos", vPos);
      formData.append("resolution", res);
      formData.append("text_color", textColor);

      const sizeVal = parseFloat(sizePercent);
      if (!sizeVal || sizeVal <= 0 || sizeVal > 100) {
        alert("사이즈(%)는 1~100 사이로 입력해 주세요.");
        setLoading(false);
        return;
      }
      formData.append("size_ratio", String(sizeVal / 100));

      if (res === "custom") {
        const widthVal = parseInt(customWidth, 10);
        const heightVal = parseInt(customHeight, 10);
        if (!widthVal || !heightVal || widthVal <= 0 || heightVal <= 0) {
          alert("가로/세로 값을 올바르게 입력해 주세요.");
          setLoading(false);
          return;
        }
        if (widthVal > MAX_CUSTOM_WIDTH || heightVal > MAX_CUSTOM_HEIGHT) {
          alert(`가로/세로는 최대 ${MAX_CUSTOM_WIDTH}x${MAX_CUSTOM_HEIGHT}까지 입력할 수 있어요.`);
          setLoading(false);
          return;
        }
        formData.append("custom_width", String(widthVal));
        formData.append("custom_height", String(heightVal));
      }

      const response = await axios.post(`${apiBase}/generate`, formData, {
        responseType: "blob",
      });

      const url = URL.createObjectURL(response.data);
      setResultImage(url);
    } catch (e) {
      console.error("서버 통신 오류:", e);
      alert(
        "이미지 생성 실패.\n\n[확인 사항]\n1. 백엔드 서버가 실행 중인지?\n2. 모든 시간표 필드가 입력됐는지?\n3. 배경 이미지가 선택됐는지?\n4. 메모리가 부족하면 더 작은 이미지를 시도해보세요."
      );
    } finally {
      setLoading(false);
    }
  };

  const updateSchedule = (index, field, value) => {
    const nextSchedules = [...schedules];
    nextSchedules[index][field] = value;
    setSchedules(nextSchedules);
  };

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h1>나만의 시간표 배경 생성기</h1>
        <a 
          href="https://github.com/gomgi851" 
          target="_blank" 
          rel="noopener noreferrer" 
          title="GitHub"
          style={{ display: "flex", alignItems: "center", textDecoration: "none" }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="currentColor"
            style={{ color: "#1a1a1a" }}
          >
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v 3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
        </a>
      </div>

      <div className="card">
        <h3>1. 배경 및 설정</h3>
        <div className="upload-section">
          <div className="upload-row">
            <label htmlFor="bg-file-input" className="bg-file-label">배경 선택</label>
            <input 
              id="bg-file-input"
              type="file" 
              accept="image/*"
              className="bg-file-input"
              onChange={(e) => {
                setBgFile(e.target.files[0]);
                setBgFileName(e.target.files[0]?.name || null);
              }} 
            />
            {bgFileName && <span className="file-name">{bgFileName}</span>}
          </div>
        </div>

        <div className="settings-row">
          <div className="setting-item">
            <label>화질</label>
            <select value={res} onChange={(e) => setRes(e.target.value)}>
              <option value="fhd">FHD (1920x1080)</option>
              <option value="qhd">QHD (2560x1440)</option>
              <option value="original">원본 화질</option>
              <option value="custom">직접 입력</option>
            </select>
          </div>
          <div className="setting-item">
            <label>표 색상</label>
            <div className="color-button-group">
              <button
                className={`color-button ${textColor === "white" ? "selected" : ""}`}
                style={{ backgroundColor: "white", borderColor: textColor === "white" ? "#333" : "#ccc" }}
                onClick={() => setTextColor("white")}
                title="하얀색"
              />
              <button
                className={`color-button ${textColor === "black" ? "selected" : ""}`}
                style={{ backgroundColor: "rgb(30,30,30)", borderColor: textColor === "black" ? "#fff" : "#ccc" }}
                onClick={() => setTextColor("black")}
                title="검은색"
              />
            </div>
          </div>
          <div className="setting-item">
            <label>가로 위치</label>
            <select value={hPos} onChange={(e) => setHPos(e.target.value)}>
              <option value="left">왼쪽</option>
              <option value="center">가운데</option>
              <option value="right">오른쪽</option>
            </select>
          </div>
          <div className="setting-item">
            <label>세로 위치</label>
            <select value={vPos} onChange={(e) => setVPos(e.target.value)}>
              <option value="top">상단</option>
              <option value="center">중앙</option>
              <option value="bottom">하단</option>
            </select>
          </div>
          <div className="setting-item">
            <label>사이즈(%)</label>
            <input
              type="number"
              min="1"
              max="100"
              value={sizePercent}
              onChange={(e) => setSizePercent(e.target.value)}
            />
          </div>
        </div>

        {res === "custom" && (
          <div className="custom-size-row">
            <div className="setting-item">
              <label>가로(px)</label>
              <input
                type="number"
                min="1"
                max={MAX_CUSTOM_WIDTH}
                value={customWidth}
                onChange={(e) => setCustomWidth(e.target.value)}
              />
            </div>
            <div className="setting-item">
              <label>세로(px)</label>
              <input
                type="number"
                min="1"
                max={MAX_CUSTOM_HEIGHT}
                value={customHeight}
                onChange={(e) => setCustomHeight(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h3>2. 수업 정보 입력</h3>
        <div className="row header-row">
          <div>요일</div>
          <div>강의명</div>
          <div>시간</div>
          <div>강의실</div>
          <div></div>
        </div>
        {schedules.map((item, index) => (
          <div key={index} className="row">
            <select className="day-select" value={item.day} onChange={(e) => updateSchedule(index, "day", e.target.value)}>
              {days.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <input
              className="name-input"
              placeholder="강의명"
              value={item.name}
              onChange={(e) => updateSchedule(index, "name", e.target.value)}
            />

            <div className="time-select-group">
              <select value={item.startH} onChange={(e) => updateSchedule(index, "startH", e.target.value)}>
                {hours.map((h) => (
                  <option key={h} value={h}>
                    {h}시
                  </option>
                ))}
              </select>
              <select value={item.startM} onChange={(e) => updateSchedule(index, "startM", e.target.value)}>
                {minutes.map((m) => (
                  <option key={m} value={m}>
                    {m}분
                  </option>
                ))}
              </select>
              <span className="time-dash">~</span>
              <select value={item.endH} onChange={(e) => updateSchedule(index, "endH", e.target.value)}>
                {hours.map((h) => (
                  <option key={h} value={h}>
                    {h}시
                  </option>
                ))}
              </select>
              <select value={item.endM} onChange={(e) => updateSchedule(index, "endM", e.target.value)}>
                {minutes.map((m) => (
                  <option key={m} value={m}>
                    {m}분
                  </option>
                ))}
              </select>
            </div>

            <input
              className="room-input"
              placeholder="강의실"
              value={item.room}
              onChange={(e) => updateSchedule(index, "room", e.target.value)}
            />
            <button className="delete-btn" onClick={() => setSchedules(schedules.filter((_, i) => i !== index))}>
              X
            </button>
          </div>
        ))}
        <button
          className="add-btn"
          onClick={() =>
            setSchedules([
              ...schedules,
              { day: "월", name: "", startH: "09", startM: "00", endH: "10", endM: "30", room: "" },
            ])
          }
        >
          + 수업 추가
        </button>
      </div>

      <div className="generate-wrapper">
        <button className="generate-btn" onClick={generateTimetable} disabled={loading}>
          {loading ? "배경화면 생성 중..." : "배경화면 생성하기"}
        </button>
      </div>

      {resultImage && (
        <div className="result-container" style={{ textAlign: "center", marginTop: "30px" }}>
          <h3>배경화면이 완성되었어요</h3>
          <img
            src={resultImage}
            alt="Result"
            style={{ maxWidth: "100%", borderRadius: "12px", boxShadow: "0 8px 20px rgba(0,0,0,0.1)" }}
          />
          <div style={{ marginTop: "15px" }}>
            <a
              href={resultImage}
              download="timetable.png"
              style={{
                display: "inline-block",
                padding: "12px 24px",
                background: "#2d3748",
                color: "#fff",
                textDecoration: "none",
                borderRadius: "8px",
                fontWeight: "bold",
              }}
            >
              이미지 저장하기
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
