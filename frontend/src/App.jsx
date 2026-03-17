import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; 

function App() {
  const [schedules, setSchedules] = useState([
    { day: '월', name: '', startH: '09', startM: '00', endH: '10', endM: '30', room: '' }
  ]);
  const [bgFile, setBgFile] = useState(null);
  const [hPos, setHPos] = useState('right');
  const [vPos, setVPos] = useState('top');
  const [res, setRes] = useState('fhd');
  const [customWidth, setCustomWidth] = useState("1920");
  const [customHeight, setCustomHeight] = useState("1080");
  const [sizePercent, setSizePercent] = useState("78");
  const [resultImage, setResultImage] = useState(null);
  const [loading, setLoading] = useState(false);

  const hours = Array.from({ length: 16 }, (_, i) => String(i + 7).padStart(2, '0'));
  const minutes = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0'));

  const generateTimetable = async () => {
    if (!bgFile) return alert("배경화면 이미지를 업로드해주세요!");
    setLoading(true);

    try {
      // ✅ [해결 핵심] 백엔드 렌더러가 검증하는 한글 키값으로 데이터를 1:1 매핑합니다.
      const formattedSchedules = schedules.map(s => ({
        "요일": s.day,
        "강의명": s.name || "미지정",
        "시작": `${s.startH}:${s.startM}`,
        "종료": `${s.endH}:${s.endM}`,
        "강의실": s.room || "장소미정"
      }));

      const formData = new FormData();
      // 백엔드 main.py에서 JSON.loads()로 처리할 수 있도록 문자열로 변환
      formData.append('schedule_data', JSON.stringify(formattedSchedules));
      formData.append('background_file', bgFile);
      formData.append('h_pos', hPos);
      formData.append('v_pos', vPos);
      formData.append('resolution', res);

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
        formData.append("custom_width", String(widthVal));
        formData.append("custom_height", String(heightVal));
      }

      const response = await axios.post('http://127.0.0.1:8000/generate', formData, { 
        responseType: 'blob' 
      });
      
      const url = URL.createObjectURL(response.data);
      setResultImage(url);
    } catch (e) {
      console.error("서버 통신 에러:", e);
      alert("이미지 생성 실패 (500 에러).\n\n[필수 체크]\n1. 백엔드 폴더에 'Jalnan2TTF.ttf' 파일이 있는지?\n2. 수업 시작 시간이 종료 시간보다 빠른지?\n3. 백엔드 터미널(VS Code 하단)의 빨간 에러 로그를 확인하세요.");
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
      <h1>🗓️ 나만의 시간표 배경 생성기</h1>

      <div className="card">
        <h3>🖼️ 1. 배경 및 설정</h3>
        <div className="upload-section upload-row">
          <label className="setting-label">배경 이미지 업로드</label>
          <input type="file" accept="image/*" onChange={(e) => setBgFile(e.target.files[0])} />
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
                value={customWidth}
                onChange={(e) => setCustomWidth(e.target.value)}
              />
            </div>
            <div className="setting-item">
              <label>세로(px)</label>
              <input
                type="number"
                min="1"
                value={customHeight}
                onChange={(e) => setCustomHeight(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h3>📅 2. 수업 정보 입력</h3>
        {schedules.map((item, index) => (
          <div key={index} className="row">
            <select className="day-select" value={item.day} onChange={(e) => updateSchedule(index, 'day', e.target.value)}>
              {['월', '화', '수', '목', '금'].map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <input className="name-input" placeholder="강의명" value={item.name} onChange={(e) => updateSchedule(index, 'name', e.target.value)} />
            
            <div className="time-select-group">
              <select value={item.startH} onChange={(e) => updateSchedule(index, 'startH', e.target.value)}>
                {hours.map(h => <option key={h} value={h}>{h}시</option>)}
              </select>
              <select value={item.startM} onChange={(e) => updateSchedule(index, 'startM', e.target.value)}>
                {minutes.map(m => <option key={m} value={m}>{m}분</option>)}
              </select>
              <span className="time-dash">~</span>
              <select value={item.endH} onChange={(e) => updateSchedule(index, 'endH', e.target.value)}>
                {hours.map(h => <option key={h} value={h}>{h}시</option>)}
              </select>
              <select value={item.endM} onChange={(e) => updateSchedule(index, 'endM', e.target.value)}>
                {minutes.map(m => <option key={m} value={m}>{m}분</option>)}
              </select>
            </div>

            <input className="room-input" placeholder="강의실" value={item.room} onChange={(e) => updateSchedule(index, 'room', e.target.value)} />
            <button className="delete-btn" onClick={() => setSchedules(schedules.filter((_, i) => i !== index))}>X</button>
          </div>
        ))}
        <button className="add-btn" onClick={() => setSchedules([...schedules, { day: '월', name: '', startH: '09', startM: '00', endH: '10', endM: '30', room: '' }])}>+ 수업 추가</button>
      </div>

      <div className="generate-wrapper">
        <button className="generate-btn" onClick={generateTimetable} disabled={loading}>
          {loading ? '⏳ 배경 생성 중...' : '🚀 배경화면 생성하기'}
        </button>
      </div>

      {resultImage && (
        <div className="result-container" style={{ textAlign: 'center', marginTop: '30px' }}>
          <h3>✨ 배경화면이 완성되었습니다!</h3>
          <img src={resultImage} alt="Result" style={{ maxWidth: '100%', borderRadius: '12px', boxShadow: '0 8px 20px rgba(0,0,0,0.1)' }} />
          <div style={{ marginTop: '15px' }}>
             <a href={resultImage} download="timetable.png" style={{ display: 'inline-block', padding: '12px 24px', background: '#2d3748', color: '#fff', textDecoration: 'none', borderRadius: '8px', fontWeight: 'bold' }}>💾 이미지 저장하기</a>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
