import json
import math
import random
import webbrowser
from datetime import datetime
import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import stat_algorithm as stat

# Global session state for the local web app
SESSION = {
    "belief": [],
    "user_name": "",
    "test_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "distance_cm": 100.0,
    "pixels_per_mm": 3.74,
    "selected_eye": "Left Eye",
    "exam_mode": "standard_20",
    "max_questions": 20,
    "question_index": 0,
    "current_size_arcmins": 2.2,
    "current_direction": "RIGHT",
    "history": [],
    # Stores completed results for "Left Eye" and "Right Eye" in current session
    "eye_results": {
        "Left Eye": None,
        "Right Eye": None
    }
}

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stanford Acuity Test (StAT) - myeyes.ai/measure (v8)</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #222222;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    padding: 10px 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  header h1 { font-size: 16px; color: #0f172a; font-weight: 700; }
  header .meta { font-size: 13px; color: #475569; }

  .screen { display: none; flex: 1; width: 100%; }
  .screen.active { display: block; }

  /* =========================================================
     STEP 1: CALIBRATION & VIEWING DISTANCE (FULL-WIDTH CARD)
     ========================================================= */
  .calib-container {
    max-width: 1060px;
    margin: 0 auto;
    padding: 22px 32px 40px 32px;
  }
  .calib-card-section {
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 22px 24px;
    background: #ffffff;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    margin-bottom: 20px;
  }
  .calib-card-section h3 {
    font-size: 18px;
    color: #0f172a;
    margin-bottom: 8px;
  }
  .preset-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin: 12px 0 16px 0;
  }
  .preset-btn {
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #f8fafc;
    color: #1e293b;
    cursor: pointer;
  }
  .preset-btn.active, .preset-btn:hover {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
  }
  .card-stage {
    width: 100%;
    min-height: 280px;
    background: #f8fafc;
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    overflow-x: auto;
  }
  #creditCardVisual {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #1d4ed8 100%);
    border-radius: 12px;
    color: #ffffff;
    position: relative;
    box-shadow: 0 8px 20px rgba(30, 58, 138, 0.28);
    border: 1px solid rgba(255,255,255,0.25);
    flex-shrink: 0;
    user-select: none;
    overflow: hidden;
  }
  .card-ruler {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 18px;
    background: rgba(255,255,255,0.15);
    border-bottom: 1px solid rgba(255,255,255,0.3);
    display: flex;
    justify-content: space-between;
    padding: 2px 8px;
    font-size: 10px;
    font-family: monospace;
  }
  #creditCardChip {
    width: 13%;
    height: 22%;
    background: linear-gradient(135deg, #fde68a, #f59e0b);
    border-radius: 5px;
    position: absolute;
    top: 34%;
    left: 7%;
    border: 1px solid #d97706;
  }
  .card-number-mock {
    position: absolute;
    top: 62%;
    left: 7%;
    font-family: 'Courier New', monospace;
    font-size: 15px;
    letter-spacing: 2px;
    font-weight: 700;
    opacity: 0.92;
  }
  .card-label-bottom {
    position: absolute;
    bottom: 8%;
    left: 7%;
    right: 7%;
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 600;
    opacity: 0.9;
  }
  .slider-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
  }
  .step-btn {
    padding: 6px 12px;
    font-size: 14px;
    font-weight: 700;
    border: 1px solid #cbd5e1;
    background: #f1f5f9;
    border-radius: 6px;
    cursor: pointer;
  }
  .step-btn:hover { background: #e2e8f0; }
  input[type="range"] { flex: 1; cursor: pointer; height: 6px; }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 20px 24px;
    background: #ffffff;
  }
  .form-row label {
    display: block;
    font-weight: 600;
    font-size: 13.5px;
    margin-bottom: 6px;
    color: #1e293b;
  }
  .form-row input, .form-row select {
    width: 100%;
    padding: 9px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 14px;
  }
  .primary-btn {
    background: #2563eb;
    color: white;
    border: none;
    padding: 13px 32px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 8px;
    cursor: pointer;
    margin-top: 18px;
  }
  .primary-btn:hover { background: #1d4ed8; }

  /* =========================================================
     STEP 2: SPLIT-SCREEN EXAM
     ========================================================= */
  .exam-layout {
    display: grid;
    grid-template-columns: 1fr 1px 430px;
    min-height: calc(100vh - 45px);
    background: #ffffff;
  }
  .vertical-sep {
    background: #e5e7eb;
    width: 1px;
    height: 100%;
  }
  .left-exam-panel {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 24px 40px 28px 40px;
  }
  .left-top-icons {
    position: absolute;
    top: 20px;
    right: 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .icon-btn {
    background: transparent;
    border: none;
    color: #9ca3af;
    font-size: 24px;
    cursor: pointer;
    line-height: 1;
    padding: 4px;
    transition: color 0.15s;
  }
  .icon-btn:hover { color: #374151; }
  .eye-title {
    font-size: 36px;
    font-weight: 400;
    color: #333333;
    letter-spacing: 0.3px;
  }
  .optotype-stage {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 360px;
  }
  #optotypeSvgContainer {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 380px;
    height: 340px;
  }
  .arrow-pad {
    display: grid;
    grid-template-columns: repeat(3, 68px);
    gap: 6px;
    margin-top: 8px;
  }
  .arrow-btn {
    padding: 6px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #d1d5db;
    background: #f9fafb;
    color: #374151;
    border-radius: 5px;
    cursor: pointer;
  }
  .arrow-btn:hover { background: #e5e7eb; }
  .progress-footer {
    font-size: 19px;
    color: #333333;
    font-weight: 400;
  }

  /* Right Panel (StAT Algorithm + 2 Stacked Charts) */
  .right-stat-panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 22px;
    background: #ffffff;
    overflow-y: auto;
  }
  .stat-heading {
    font-size: 32px;
    font-weight: 400;
    color: #333333;
    margin-bottom: 10px;
  }
  .stat-metrics-block {
    font-size: 15.5px;
    color: #777777;
    text-align: center;
    line-height: 1.5;
    margin-bottom: 12px;
  }
  .stat-metrics-block .spacer {
    height: 6px;
  }
  .chart-card {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 10px;
  }
  .chart-subtitle {
    font-size: 14.5px;
    color: #777777;
    margin-bottom: 2px;
  }
  canvas.stat-chart {
    width: 385px;
    height: 190px;
    display: block;
  }

  /* =========================================================
     MODAL DIALOG AFTER 20 QUESTIONS ("Continue or Finish?")
     ========================================================= */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.55);
    z-index: 1000;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }
  .modal-overlay.active {
    display: flex;
  }
  .modal-box {
    background: #ffffff;
    border-radius: 14px;
    max-width: 520px;
    width: 92%;
    padding: 28px 30px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.22);
    text-align: center;
    border: 1px solid #e2e8f0;
  }
  .modal-box h3 {
    font-size: 22px;
    color: #0f172a;
    margin-bottom: 8px;
  }
  .modal-box p.sub {
    font-size: 14.5px;
    color: #475569;
    margin-bottom: 16px;
    line-height: 1.5;
  }
  .modal-stats {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 20px;
    font-size: 15px;
    color: #1e293b;
    line-height: 1.65;
  }
  .modal-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .modal-btn-row {
    display: flex;
    gap: 10px;
    justify-content: center;
  }
  .btn-continue {
    flex: 1;
    background: #f1f5f9;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    padding: 11px 16px;
    font-size: 14.5px;
    font-weight: 600;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-continue:hover { background: #e2e8f0; }
  .btn-finish {
    width: 100%;
    background: #2e77b5;
    color: #ffffff;
    border: none;
    padding: 13px 20px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-finish:hover { background: #235d91; }

  /* =========================================================
     STEP 3: FINAL RESULTS + 0-100 SCORE + VISION HISTORY
     ========================================================= */
  .results-page-wrap {
    max-width: 1040px;
    margin: 0 auto;
    padding: 28px 32px 60px 32px;
    text-align: center;
  }
  .user-session-banner {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 18px;
    align-items: center;
    justify-content: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 9px 20px;
    margin-bottom: 20px;
    font-size: 14.5px;
    color: #334155;
  }

  /* Eye Top Buttons (✔ Left Eye Done | + Test Right Eye) */
  .eye-top-buttons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 28px;
    max-width: 860px;
    margin: 0 auto 22px auto;
  }
  .eye-action-btn {
    background: #2e77b5;
    color: #ffffff;
    border: 1px solid #266499;
    padding: 11px 24px;
    font-size: 17px;
    font-weight: 400;
    border-radius: 5px;
    cursor: pointer;
    justify-self: center;
    min-width: 175px;
    transition: background 0.15s;
  }
  .eye-action-btn:hover { background: #245f91; }

  /* Two Side-by-Side Result Cards */
  .eye-cards-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 28px;
    max-width: 860px;
    margin: 0 auto 26px auto;
    align-items: stretch;
  }
  .eye-result-card {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 22px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }
  .eye-result-card h4 {
    font-size: 17px;
    font-weight: 700;
    color: #333333;
    margin-bottom: 12px;
  }
  .score-100-badge {
    display: inline-block;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    font-weight: 700;
    font-size: 15px;
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 12px;
  }
  .eye-result-card .metric-line {
    font-size: 17px;
    color: #333333;
    line-height: 1.48;
    margin-bottom: 12px;
  }
  .eye-result-card .no-result-text {
    font-size: 17px;
    font-style: italic;
    color: #555555;
    margin: 28px 0;
  }
  .dist-plots-wrap {
    margin-top: 10px;
    background: #ffffff;
    border-radius: 6px;
    padding: 12px 10px;
    box-shadow: inset 0 0 0 1px #e5e7eb;
  }
  .dist-plots-title {
    font-size: 13px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 6px;
  }
  canvas.result-dist-canvas {
    width: 360px;
    height: 155px;
    display: block;
    margin: 0 auto 10px auto;
  }

  /* Bottom Unit Selector & Save Results Buttons */
  .bottom-controls-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
  }
  .unit-select-wrapper {
    position: relative;
    display: inline-block;
  }
  .unit-select-btn {
    appearance: none;
    -webkit-appearance: none;
    background: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 9px 30px 9px 16px;
    font-size: 16px;
    color: #333333;
    cursor: pointer;
    min-width: 210px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }
  .unit-select-btn:hover { background: #f9f9f9; border-color: #b3b3b3; }
  .save-results-btn {
    background: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 9px 22px;
    font-size: 16px;
    color: #333333;
    cursor: pointer;
    min-width: 190px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }
  .save-results-btn:hover { background: #f3f4f6; border-color: #b3b3b3; }

  /* Vision History Over Time Section */
  .history-section {
    max-width: 860px;
    margin: 36px auto 0 auto;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 20px 24px;
    background: #ffffff;
    text-align: left;
  }
  .history-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
  }
  .history-header-row h3 {
    font-size: 18px;
    color: #0f172a;
  }
  #historyTrendCanvas {
    width: 100%;
    height: 210px;
    display: block;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 14px;
  }
  .trace-details {
    max-width: 860px;
    margin: 24px auto 0 auto;
    text-align: left;
  }
  .trace-details summary {
    cursor: pointer;
    font-weight: 600;
    color: #475569;
    font-size: 14.5px;
    padding: 8px 0;
  }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 10px; }
  th, td { border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: center; }
  th { background: #f1f5f9; font-weight: 600; }
</style>
</head>
<body>

<header>
  <h1>Stanford Acuity Test (StAT) — myeyes.ai/measure (v8)</h1>
  <div class="meta" id="headerMeta">Step 1: Screen Calibration & Patient Info</div>
</header>

<!-- =========================================================
     SCREEN 1: CALIBRATION, USER NAME & DATE, VIEWING DISTANCE
     ========================================================= -->
<div id="screenCalib" class="screen active">
  <div class="calib-container">
    <h2 style="font-size: 23px; margin-bottom: 6px; color: #0f172a;">
      Step 1: Screen Calibration, Patient Info & Viewing Distance
    </h2>
    <p style="color: #475569; font-size: 14.5px; margin-bottom: 16px;">
      Automatically calibrated for a <b>15.6-inch laptop screen</b>. Place a real bank/ID card (85.60 mm × 53.98 mm) on the blue card below to verify or fine-tune.
    </p>

    <div class="calib-card-section">
      <h3>1. Exact Credit / Bank Card Calibration (85.60 mm × 53.98 mm)</h3>
      <div class="preset-row">
        <span style="font-size: 13.5px; font-weight: 600; color: #334155;">Auto-Set by Laptop Screen Size:</span>
        <button class="preset-btn" onclick="setDiagonalPreset(13.3, this)">13.3"</button>
        <button class="preset-btn" onclick="setDiagonalPreset(14.0, this)">14.0"</button>
        <button class="preset-btn active" id="defaultPresetBtn" onclick="setDiagonalPreset(15.6, this)">15.6" (Standard Laptop)</button>
        <button class="preset-btn" onclick="setDiagonalPreset(16.0, this)">16.0"</button>
        <button class="preset-btn" onclick="setDiagonalPreset(17.3, this)">17.3"</button>
        <button class="preset-btn" onclick="setDiagonalPreset(24.0, this)">24.0" Monitor</button>
        <button class="preset-btn" onclick="setDiagonalPreset(27.0, this)">27.0" Monitor</button>
      </div>

      <div class="card-stage">
        <div id="creditCardVisual">
          <div class="card-ruler">
            <span>0mm</span><span>20mm</span><span>40mm</span><span>60mm</span><span>85.6mm</span>
          </div>
          <div id="creditCardChip"></div>
          <div class="card-number-mock">5412  7534  8901  2345</div>
          <div class="card-label-bottom">
            <span>ISO/IEC 7810 STANDARD CARD</span>
            <span>85.60 mm × 53.98 mm</span>
          </div>
        </div>
      </div>

      <div class="slider-controls">
        <button class="step-btn" onclick="nudgeCardWidth(-2)">− Smaller</button>
        <input type="range" id="cardSlider" min="160" max="720" step="0.5" value="360" oninput="onSliderChange()">
        <button class="step-btn" onclick="nudgeCardWidth(2)">+ Larger</button>
      </div>
      <p id="ppiDisplay" style="font-weight: 700; color: #2563eb; margin-top: 10px; font-size: 14px; text-align: center;"></p>
    </div>

    <div class="settings-grid">
      <div class="form-row">
        <label>User / Patient Name (Optional):</label>
        <input type="text" id="userNameInput" placeholder="Optional (e.g., Ali)">
        <small style="color: #64748b; display: block; margin-top: 4px;">
          Used to track your vision over time.
        </small>
      </div>

      <div class="form-row">
        <label>Date of Test:</label>
        <input type="text" id="testDateInput" value="">
        <small style="color: #64748b; display: block; margin-top: 4px;">
          Recorded in your history & saved report.
        </small>
      </div>

      <div class="form-row">
        <label>Distance from Laptop (cm):</label>
        <input type="number" id="distanceInput" value="100" min="35" max="400" step="5">
        <small style="color: #64748b; display: block; margin-top: 4px;">
          Sit comfortably (e.g., 80–120 cm).
        </small>
      </div>

      <div class="form-row">
        <label>Eye to Test First:</label>
        <select id="eyeSelect">
          <option value="Left Eye">Left Eye (Cover Right Eye)</option>
          <option value="Right Eye">Right Eye (Cover Left Eye)</option>
        </select>
      </div>

      <div class="form-row">
        <label>Initial Question Batch:</label>
        <select id="modeSelect">
          <option value="standard_20">20 Questions (Ask to continue)</option>
          <option value="stat_star">StAT-star (95% Confidence)</option>
        </select>
      </div>
    </div>

    <div style="text-align: center;">
      <button class="primary-btn" onclick="startExamForSelectedEye()">Start StAT Vision Exam →</button>
    </div>
  </div>
</div>

<!-- =========================================================
     SCREEN 2: INTERACTIVE EXAM
     ========================================================= -->
<div id="screenExam" class="screen">
  <div class="exam-layout">
    <!-- LEFT PANEL -->
    <div class="left-exam-panel">
      <div class="left-top-icons">
        <button class="icon-btn" title="Return to Calibration / Setup" onclick="showScreen('screenCalib')">✖</button>
        <button class="icon-btn" title="Toggle Right Panel" onclick="toggleRightPanel()">📶</button>
      </div>

      <div class="eye-title" id="eyeHeader">Left Eye</div>

      <div class="optotype-stage">
        <div id="optotypeSvgContainer"></div>

        <div class="arrow-pad">
          <div></div>
          <button class="arrow-btn" onclick="sendAnswer('UP')">↑ Up</button>
          <div></div>
          <button class="arrow-btn" onclick="sendAnswer('LEFT')">← Left</button>
          <button class="arrow-btn" onclick="sendAnswer('DOWN')">↓ Down</button>
          <button class="arrow-btn" onclick="sendAnswer('RIGHT')">Right →</button>
        </div>
      </div>

      <div class="progress-footer" id="progressText">Progress: 0%</div>
    </div>

    <div class="vertical-sep" id="panelDivider"></div>

    <!-- RIGHT PANEL: StAT Algorithm + TWO STACKED CHARTS -->
    <div class="right-stat-panel" id="rightStatPanel">
      <div class="stat-heading">StAT Algorithm</div>

      <div class="stat-metrics-block" id="statMetrics">
        N done: 0<br>
        Curr size: 2.2 arcmin<br>
        Curr size: 0.3 logMAR
        <div class="spacer"></div>
        MAP acuity: 2.0 arcmin<br>
        MAP acuity: 0.3 logMAR<br>
        Vision Score (0-100): 50
        <div class="spacer"></div>
        Interval: [0.5, 12.6] arcmins
      </div>

      <!-- CHART 1 (TOP): Acuity in arcmins -->
      <div class="chart-card">
        <div class="chart-subtitle">Likelihood of Acuity Scores (arcmins):</div>
        <canvas id="curveCanvasArcmin" class="stat-chart"></canvas>
      </div>

      <!-- CHART 2 (BOTTOM): Acuity in logMAR -->
      <div class="chart-card">
        <div class="chart-subtitle">Likelihood of Acuity Scores (logMAR):</div>
        <canvas id="curveCanvasLogmar" class="stat-chart"></canvas>
      </div>
    </div>
  </div>
</div>

<!-- =========================================================
     MODAL DIALOG: "20 QUESTIONS COMPLETED — CONTINUE OR FINISH?" (IN ENGLISH)
     ========================================================= -->
<div id="continueModal" class="modal-overlay">
  <div class="modal-box">
    <h3 id="modalTitle">20 Questions Completed!</h3>
    <p class="sub">
      Would you like to continue with additional questions to further refine accuracy, or finish the exam for this eye and view your results?
    </p>
    <div class="modal-stats" id="modalStatsSummary"></div>
    <div class="modal-actions">
      <div class="modal-btn-row">
        <button class="btn-continue" onclick="continueExam(10)">+ Continue (+10 Questions)</button>
        <button class="btn-continue" onclick="continueExam(20)">+ Continue (+20 Questions)</button>
      </div>
      <button class="btn-finish" onclick="finishExamNow()">✔ Finish & View Results</button>
    </div>
  </div>
</div>

<!-- =========================================================
     SCREEN 3: FINAL RESULTS + 0-100 SCORE + VISION HISTORY OVER TIME
     ========================================================= -->
<div id="screenResults" class="screen">
  <div class="results-page-wrap">
    <!-- User Name & Date Banner -->
    <div class="user-session-banner" id="userSessionBanner">
      <span><b>Patient / User:</b> <span id="bannerUserName">Guest</span></span>
      <span>|</span>
      <span><b>Date of Test:</b> <span id="bannerTestDate">--</span></span>
      <button class="step-btn" style="font-size:12px; padding:4px 10px;" onclick="showScreen('screenCalib')">✎ Edit Setup / Name</button>
    </div>

    <!-- Top Eye Action Buttons -->
    <div class="eye-top-buttons">
      <button class="eye-action-btn" id="btnLeftEyeAction" onclick="startExamForEye('Left Eye')">
        ✔ Left Eye Done
      </button>
      <button class="eye-action-btn" id="btnRightEyeAction" onclick="startExamForEye('Right Eye')">
        + Test Right Eye
      </button>
    </div>

    <!-- Side-by-Side Result Cards (Left Eye Results | Right Eye Results) -->
    <div class="eye-cards-grid">
      <!-- Left Eye Card -->
      <div class="eye-result-card" id="leftEyeCard">
        <h4>Left Eye Results</h4>
        <div id="leftEyeContent">
          <div class="no-result-text">No results yet</div>
        </div>
      </div>

      <!-- Right Eye Card -->
      <div class="eye-result-card" id="rightEyeCard">
        <h4>Right Eye Results</h4>
        <div id="rightEyeContent">
          <div class="no-result-text">No results yet</div>
        </div>
      </div>
    </div>

    <!-- Bottom Controls: Unit Switcher (including Score 0-100 / 100+) + Save Results -->
    <div class="bottom-controls-stack">
      <div class="unit-select-wrapper">
        <select id="unitSelector" class="unit-select-btn" onchange="renderBothEyeCards()">
          <option value="score_100">⚙ Score (0–100 / 100+) ▾</option>
          <option value="arcmin" selected>⚙ ArcMin Units ▾</option>
          <option value="logmar">⚙ LogMAR Units ▾</option>
          <option value="snellen_ft">⚙ Snellen (20/X) ▾</option>
          <option value="snellen_m">⚙ Snellen (6/X) ▾</option>
          <option value="decimal">⚙ Decimal Units ▾</option>
        </select>
      </div>

      <button class="save-results-btn" onclick="saveResultsAsImage()">
        <span>⬇</span> <span>Save Results</span>
      </button>

      <button class="save-results-btn" style="font-size: 13.5px; padding: 6px 16px; color: #555;" onclick="saveResultsAsJSON()">
        <span>📄</span> <span>Save Raw Data (JSON)</span>
      </button>
    </div>

    <!-- VISION HISTORY OVER TIME SECTION -->
    <div class="history-section">
      <div class="history-header-row">
        <h3>📈 Vision History Over Time (0–100 Score & Acuity Log)</h3>
        <div style="display:flex; gap:8px; align-items:center;">
          <select id="historyUserFilter" style="padding:5px 10px; border:1px solid #cbd5e1; border-radius:6px; font-size:13px;" onchange="renderVisionHistorySection()">
            <option value="ALL">All Users</option>
          </select>
          <button class="step-btn" style="font-size:12.5px;" onclick="exportHistoryCSV()">⬇ Export CSV</button>
          <button class="step-btn" style="font-size:12.5px; color:#dc2626;" onclick="clearVisionHistory()">🗑 Clear History</button>
        </div>
      </div>

      <canvas id="historyTrendCanvas" width="810" height="210"></canvas>

      <table>
        <thead>
          <tr>
            <th>Date of Test</th>
            <th>User Name</th>
            <th>Eye</th>
            <th>Score (0–100)</th>
            <th>Acuity (arcmin)</th>
            <th>LogMAR</th>
            <th>Snellen</th>
            <th>95% Interval (arcmin)</th>
          </tr>
        </thead>
        <tbody id="visionHistoryTableBody"></tbody>
      </table>
    </div>

    <!-- Expandable Question-by-Question Trace -->
    <details class="trace-details">
      <summary>View Question-by-Question Bayesian Trace (Current Session)</summary>
      <table>
        <thead>
          <tr>
            <th>Eye</th>
            <th>N done</th>
            <th>Size Shown (arcmin)</th>
            <th>Size Shown (logMAR)</th>
            <th>Direction</th>
            <th>Answer</th>
            <th>Outcome</th>
            <th>MAP Acuity</th>
            <th>Score (0–100)</th>
          </tr>
        </thead>
        <tbody id="historyTableBody"></tbody>
      </table>
    </details>
  </div>
</div>

<script>
const CARD_WIDTH_MM = 85.60;
const CARD_HEIGHT_MM = 53.98;
let pixelsPerMm = 3.74;
let examActive = false;
let currentDiagonalInches = 15.6;
let latestResultsPayload = null;

function formatCurrentDateTime() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const hh = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
}

function arcminToScore0_100(arcminVal) {
  const v = Math.max(0.05, parseFloat(arcminVal));
  const raw = Math.round(100.0 / v);
  if (raw > 100) {
    return { text: '100+', numeric: 105 };
  }
  const clamped = Math.max(0, Math.min(100, raw));
  return { text: String(clamped), numeric: clamped };
}

function setDiagonalPreset(diagInches, btnEl) {
  currentDiagonalInches = diagInches;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  const sw = window.screen.width || window.innerWidth || 1536;
  const sh = window.screen.height || window.innerHeight || 864;
  const aspect = sw / sh;
  const diagMm = diagInches * 25.4;
  const screenWidthMm = diagMm * (aspect / Math.sqrt(aspect * aspect + 1.0));

  pixelsPerMm = sw / screenWidthMm;
  const exactCardWidthPx = CARD_WIDTH_MM * pixelsPerMm;

  const slider = document.getElementById('cardSlider');
  slider.value = exactCardWidthPx.toFixed(1);
  applyCardWidthPx(exactCardWidthPx);
}

function onSliderChange() {
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  const widthPx = parseFloat(document.getElementById('cardSlider').value);
  applyCardWidthPx(widthPx);
}

function nudgeCardWidth(deltaPx) {
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  const slider = document.getElementById('cardSlider');
  const nextVal = Math.max(160, Math.min(720, parseFloat(slider.value) + deltaPx));
  slider.value = nextVal;
  applyCardWidthPx(nextVal);
}

function applyCardWidthPx(widthPx) {
  const heightPx = widthPx * (CARD_HEIGHT_MM / CARD_WIDTH_MM);
  pixelsPerMm = widthPx / CARD_WIDTH_MM;
  const ppi = pixelsPerMm * 25.4;

  const card = document.getElementById('creditCardVisual');
  card.style.width = widthPx + 'px';
  card.style.height = heightPx + 'px';

  document.getElementById('ppiDisplay').innerText =
    `Card Size on Screen: ${Math.round(widthPx)} px × ${Math.round(heightPx)} px  |  Scale: ${pixelsPerMm.toFixed(2)} px/mm (${Math.round(ppi)} CSS PPI) — Matches 85.6 mm × 53.98 mm`;
}

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  examActive = (id === 'screenExam');
}

function toggleRightPanel() {
  const rp = document.getElementById('rightStatPanel');
  const sep = document.getElementById('panelDivider');
  if (rp.style.display === 'none') {
    rp.style.display = 'flex';
    sep.style.display = 'block';
  } else {
    rp.style.display = 'none';
    sep.style.display = 'none';
  }
}

function startExamForSelectedEye() {
  const eye = document.getElementById('eyeSelect').value;
  startExamForEye(eye);
}

async function startExamForEye(eyeName) {
  document.getElementById('eyeSelect').value = eyeName;
  const userName = document.getElementById('userNameInput').value.trim();
  let testDate = document.getElementById('testDateInput').value.trim();
  if (!testDate) {
    testDate = formatCurrentDateTime();
    document.getElementById('testDateInput').value = testDate;
  }
  const distanceCm = parseFloat(document.getElementById('distanceInput').value) || 100;
  const mode = document.getElementById('modeSelect').value;

  const res = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_name: userName,
      test_date: testDate,
      distance_cm: distanceCm,
      pixels_per_mm: pixelsPerMm,
      selected_eye: eyeName,
      exam_mode: mode
    })
  });
  const data = await res.json();
  document.getElementById('eyeHeader').innerText = data.selected_eye;
  const displayUser = data.user_name ? `User: ${data.user_name} | ` : '';
  document.getElementById('headerMeta').innerText =
    `${displayUser}Date: ${data.test_date} | Distance: ${distanceCm} cm | Eye: ${eyeName}`;
  document.getElementById('continueModal').classList.remove('active');
  showScreen('screenExam');
  renderExamState(data);
}

async function sendAnswer(direction) {
  if (!examActive) return;
  if (document.getElementById('continueModal').classList.contains('active')) return;

  const res = await fetch('/api/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer: direction })
  });
  const data = await res.json();
  renderExamState(data);

  if (data.ask_continue) {
    showContinueModal(data);
  } else if (data.finished) {
    latestResultsPayload = data;
    renderResultsScreen(data);
    showScreen('screenResults');
  }
}

function showContinueModal(data) {
  const sc = arcminToScore0_100(data.map_k1);
  document.getElementById('modalTitle').innerText =
    `${data.question_index} Questions Completed (${data.selected_eye})`;
  document.getElementById('modalStatsSummary').innerHTML =
    `<b>Vision Score (0–100):</b> <span style="color:#2563eb; font-weight:700;">${sc.text}</span><br>` +
    `<b>Current MAP Acuity:</b> ${data.map_k1.toFixed(2)} arcmin (${data.map_logmar.toFixed(2)} logMAR | ${data.snellen_feet})<br>` +
    `<b>95% Confidence Interval:</b> [${data.ci_low.toFixed(1)}, ${data.ci_high.toFixed(1)}] arcmins<br>` +
    `<b>Calibrated Confidence (±10%):</b> ${(data.confidence * 100).toFixed(1)}%`;
  document.getElementById('continueModal').classList.add('active');
}

async function continueExam(extraQuestions) {
  const res = await fetch('/api/continue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extra_questions: extraQuestions })
  });
  const data = await res.json();
  document.getElementById('continueModal').classList.remove('active');
  renderExamState(data);
}

async function finishExamNow() {
  const res = await fetch('/api/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  const data = await res.json();
  document.getElementById('continueModal').classList.remove('active');
  latestResultsPayload = data;
  renderResultsScreen(data);
  showScreen('screenResults');
}

window.addEventListener('keydown', (e) => {
  if (!examActive) return;
  if (document.getElementById('continueModal').classList.contains('active')) return;
  if (e.key === 'ArrowUp') { e.preventDefault(); sendAnswer('UP'); }
  else if (e.key === 'ArrowDown') { e.preventDefault(); sendAnswer('DOWN'); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); sendAnswer('LEFT'); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); sendAnswer('RIGHT'); }
});

function renderExamState(data) {
  drawCrispSvgTumblingE(data.letter_height_px, data.current_direction);
  document.getElementById('progressText').innerText = `Progress: ${data.progress_pct}%`;

  const currLogmar = Math.log10(data.current_size_arcmins);
  const scoreObj = arcminToScore0_100(data.map_k1);

  document.getElementById('statMetrics').innerHTML =
    `N done: ${data.question_index}<br>` +
    `Curr size: ${data.current_size_arcmins.toFixed(1)} arcmin<br>` +
    `Curr size: ${currLogmar.toFixed(1)} logMAR` +
    `<div class="spacer"></div>` +
    `MAP acuity: ${data.map_k1.toFixed(1)} arcmin (${data.snellen_feet})<br>` +
    `MAP acuity: ${data.map_logmar.toFixed(1)} logMAR<br>` +
    `<b>Vision Score (0–100): ${scoreObj.text}</b>` +
    `<div class="spacer"></div>` +
    `Interval: [${data.ci_low.toFixed(1)}, ${data.ci_high.toFixed(1)}] arcmins`;

  drawArcminsChart(document.getElementById('curveCanvasArcmin'), 385, 190, data.curve_arc_xs, data.curve_arc_ys);
  drawLogmarChart(document.getElementById('curveCanvasLogmar'), 385, 190, data.curve_log_xs, data.curve_log_ys);
}

function drawCrispSvgTumblingE(totalPx, direction) {
  const container = document.getElementById('optotypeSvgContainer');
  const sizePx = Math.max(4.0, Math.min(320.0, totalPx));

  let angle = 0;
  if (direction === 'RIGHT') angle = 0;
  else if (direction === 'DOWN') angle = 90;
  else if (direction === 'LEFT') angle = 180;
  else if (direction === 'UP') angle = -90;

  container.innerHTML = `
    <svg width="${sizePx}" height="${sizePx}" viewBox="0 0 5 5"
         shape-rendering="crispEdges" style="overflow: visible;">
      <g transform="rotate(${angle} 2.5 2.5)">
        <path d="M0,0 H5 V1 H1 V2 H5 V3 H1 V4 H5 V5 H0 Z" fill="#000000" />
      </g>
    </svg>
  `;
}

function setupHiDPICanvas(canvas, cssW, cssH) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.width = cssW + 'px';
  canvas.style.height = cssH + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  return ctx;
}

function getNiceYAxis(ys) {
  const maxVal = Math.max(...ys, 0.08);
  let step = 0.025;
  if (maxVal <= 0.10) step = 0.025;
  else if (maxVal <= 0.20) step = 0.05;
  else if (maxVal <= 0.40) step = 0.10;
  else if (maxVal <= 0.60) step = 0.15;
  else if (maxVal <= 0.80) step = 0.20;
  else step = 0.25;

  const topTick = 4.0 * step;
  const axisCeiling = Math.max(topTick * 1.03, maxVal * 1.05);
  const ticks = [];
  for (let i = 0; i <= 4; i++) {
    const tv = +(i * step).toFixed(4);
    let label = '0';
    if (i > 0) {
      if (Math.abs(tv * 10 - Math.round(tv * 10)) < 1e-6) {
        label = tv.toFixed(1);
      } else {
        label = tv.toFixed(3).replace(/0+$/, '').replace(/^0/, '');
      }
    }
    ticks.push({ value: tv, label: label });
  }
  return { axisCeiling, ticks };
}

function drawArcminsChart(canvas, W, H, xs, ys) {
  const ctx = setupHiDPICanvas(canvas, W, H);
  const padL = 44, padR = 12, padT = 16, padB = 34;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const { axisCeiling, ticks } = getNiceYAxis(ys);
  const x0 = padL, y0 = padT + plotH;

  ctx.strokeStyle = '#d1d5db';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  for (let xt = 0; xt <= 12; xt += 2) {
    const px = x0 + (xt / 12.0) * plotW;
    ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, y0); ctx.stroke();
  }
  ticks.forEach((tk, i) => {
    if (i === 0) return;
    const py = y0 - (tk.value / axisCeiling) * plotH;
    ctx.beginPath(); ctx.moveTo(x0, py); ctx.lineTo(x0 + plotW, py); ctx.stroke();
  });
  ctx.setLineDash([]);

  ctx.strokeStyle = '#6b7280';
  ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x0, padT); ctx.lineTo(x0, y0); ctx.lineTo(x0 + plotW, y0); ctx.stroke();

  ctx.fillStyle = '#4b5563';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  for (let xt = 0; xt <= 12; xt += 2) {
    const px = x0 + (xt / 12.0) * plotW;
    ctx.beginPath(); ctx.moveTo(px, y0); ctx.lineTo(px, y0 + 4); ctx.stroke();
    ctx.fillText(xt.toString(), px, y0 + 15);
  }
  ctx.fillStyle = '#111827';
  ctx.font = '12.5px sans-serif';
  ctx.fillText('Acuity (arcmins)', x0 + plotW / 2, y0 + 29);

  ctx.fillStyle = '#4b5563';
  ctx.font = '10.5px sans-serif';
  ctx.textAlign = 'right';
  ticks.forEach(tk => {
    const py = y0 - (tk.value / axisCeiling) * plotH;
    ctx.beginPath(); ctx.moveTo(x0 - 4, py); ctx.lineTo(x0, py); ctx.stroke();
    ctx.fillText(tk.label, x0 - 6, py + 4);
  });

  ctx.beginPath();
  xs.forEach((xv, i) => {
    const px = x0 + (xv / 12.0) * plotW;
    const py = y0 - (ys[i] / axisCeiling) * plotH;
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.strokeStyle = '#e15759';
  ctx.lineWidth = 1.6;
  ctx.stroke();

  const legX = x0 + plotW * 0.25;
  const legY = padT + 8;
  ctx.strokeStyle = '#e15759';
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(legX - 16, legY); ctx.lineTo(legX - 2, legY); ctx.stroke();
  ctx.beginPath(); ctx.arc(legX - 9, legY, 2.2, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#555555';
  ctx.textAlign = 'left';
  ctx.font = '12px sans-serif';
  ctx.fillText('likelihood', legX + 2, legY + 4);
}

function drawLogmarChart(canvas, W, H, xs, ys) {
  const ctx = setupHiDPICanvas(canvas, W, H);
  const padL = 44, padR = 12, padT = 16, padB = 34;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const minX = -0.8, maxX = 1.25;
  const rangeX = maxX - minX;
  const { axisCeiling, ticks } = getNiceYAxis(ys);
  const x0 = padL, y0 = padT + plotH;

  ctx.strokeStyle = '#d1d5db';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  const xTicks = [-0.8, -0.4, 0, 0.4, 0.8, 1.2];
  xTicks.forEach(xt => {
    const px = x0 + ((xt - minX) / rangeX) * plotW;
    ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, y0); ctx.stroke();
  });
  ticks.forEach((tk, i) => {
    if (i === 0) return;
    const py = y0 - (tk.value / axisCeiling) * plotH;
    ctx.beginPath(); ctx.moveTo(x0, py); ctx.lineTo(x0 + plotW, py); ctx.stroke();
  });
  ctx.setLineDash([]);

  ctx.strokeStyle = '#6b7280';
  ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x0, padT); ctx.lineTo(x0, y0); ctx.lineTo(x0 + plotW, y0); ctx.stroke();

  ctx.fillStyle = '#4b5563';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  xTicks.forEach(xt => {
    const px = x0 + ((xt - minX) / rangeX) * plotW;
    ctx.beginPath(); ctx.moveTo(px, y0); ctx.lineTo(px, y0 + 4); ctx.stroke();
    const lbl = xt === 0 ? '0' : xt.toFixed(1);
    ctx.fillText(lbl, px, y0 + 15);
  });
  ctx.fillStyle = '#111827';
  ctx.font = '12.5px sans-serif';
  ctx.fillText('Acuity (logMAR)', x0 + plotW / 2, y0 + 29);

  ctx.fillStyle = '#4b5563';
  ctx.font = '10.5px sans-serif';
  ctx.textAlign = 'right';
  ticks.forEach(tk => {
    const py = y0 - (tk.value / axisCeiling) * plotH;
    ctx.beginPath(); ctx.moveTo(x0 - 4, py); ctx.lineTo(x0, py); ctx.stroke();
    ctx.fillText(tk.label, x0 - 6, py + 4);
  });

  ctx.beginPath();
  xs.forEach((xv, i) => {
    const px = x0 + ((xv - minX) / rangeX) * plotW;
    const py = y0 - (ys[i] / axisCeiling) * plotH;
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.strokeStyle = '#7970C6';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  const legX = x0 + plotW * 0.25;
  const legY = padT + 8;
  ctx.strokeStyle = '#7970C6';
  ctx.lineWidth = 1.4;
  ctx.beginPath(); ctx.moveTo(legX - 16, legY); ctx.lineTo(legX - 2, legY); ctx.stroke();
  ctx.beginPath(); ctx.arc(legX - 9, legY, 2.2, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#555555';
  ctx.textAlign = 'left';
  ctx.font = '12px sans-serif';
  ctx.fillText('likelihood', legX + 2, legY + 4);
}

// =========================================================================
// STEP 3: RESULTS RENDERING (INCLUDING 0-100 / 100+ & VISION HISTORY)
// =========================================================================

function formatAcuityByUnit(arcminVal, unit) {
  const v = Math.max(0.05, arcminVal);
  if (unit === 'score_100') {
    const s = arcminToScore0_100(v);
    return `${s.text} (0–100 scale)`;
  }
  if (unit === 'arcmin') return `${v.toFixed(1)} arcmin`;
  if (unit === 'logmar') return `${Math.log10(v).toFixed(2)} logMAR`;
  if (unit === 'snellen_ft') return `20/${Math.round(20 * v)}`;
  if (unit === 'snellen_m') return `6/${(6 * v).toFixed(1)}`;
  if (unit === 'decimal') return `${(1.0 / v).toFixed(2)}`;
  return `${v.toFixed(1)} arcmin`;
}

function formatIntervalByUnit(ciLow, ciHigh, unit) {
  const lo = Math.max(0.05, ciLow);
  const hi = Math.max(0.05, ciHigh);
  if (unit === 'score_100') {
    // Smaller arcmin = higher 0-100 score
    const lowScore = arcminToScore0_100(hi).text;
    const highScore = arcminToScore0_100(lo).text;
    return `${lowScore} &nbsp;to&nbsp; ${highScore}`;
  }
  if (unit === 'arcmin') return `${lo.toFixed(1)} &nbsp;to&nbsp; ${hi.toFixed(1)} arcmin`;
  if (unit === 'logmar') return `${Math.log10(lo).toFixed(2)} &nbsp;to&nbsp; ${Math.log10(hi).toFixed(2)} logMAR`;
  if (unit === 'snellen_ft') return `20/${Math.round(20 * lo)} &nbsp;to&nbsp; 20/${Math.round(20 * hi)}`;
  if (unit === 'snellen_m') return `6/${(6 * lo).toFixed(1)} &nbsp;to&nbsp; 6/${(6 * hi).toFixed(1)}`;
  if (unit === 'decimal') return `${(1.0 / hi).toFixed(2)} &nbsp;to&nbsp; ${(1.0 / lo).toFixed(2)}`;
  return `${lo.toFixed(1)} &nbsp;to&nbsp; ${hi.toFixed(1)} arcmin`;
}

function renderResultsScreen(data) {
  latestResultsPayload = data;
  const eyeRes = data.eye_results || {};

  document.getElementById('bannerUserName').innerText = data.user_name ? data.user_name : 'Guest (Not specified)';
  document.getElementById('bannerTestDate').innerText = data.test_date || formatCurrentDateTime();

  const btnL = document.getElementById('btnLeftEyeAction');
  const btnR = document.getElementById('btnRightEyeAction');
  btnL.innerText = eyeRes['Left Eye'] ? '✔ Left Eye Done' : '+ Test Left Eye';
  btnR.innerText = eyeRes['Right Eye'] ? '✔ Right Eye Done' : '+ Test Right Eye';

  renderBothEyeCards();
  renderTraceTable(eyeRes);
  populateUserFilterDropdown(data.vision_history || []);
  renderVisionHistorySection();
}

function renderBothEyeCards() {
  if (!latestResultsPayload || !latestResultsPayload.eye_results) return;
  const unit = document.getElementById('unitSelector').value;
  const eyeRes = latestResultsPayload.eye_results;

  renderSingleEyeCard('Left Eye', 'leftEyeContent', eyeRes['Left Eye'], unit, 'left');
  renderSingleEyeCard('Right Eye', 'rightEyeContent', eyeRes['Right Eye'], unit, 'right');
}

function renderSingleEyeCard(eyeName, containerId, resObj, unit, prefix) {
  const container = document.getElementById(containerId);
  if (!resObj) {
    container.innerHTML = `<div class="no-result-text">No results yet</div>`;
    return;
  }

  const scoreStr = formatAcuityByUnit(resObj.map_k1, unit);
  const intervalStr = formatIntervalByUnit(resObj.ci_low, resObj.ci_high, unit);
  const score100 = arcminToScore0_100(resObj.map_k1);
  const score100Interval = formatIntervalByUnit(resObj.ci_low, resObj.ci_high, 'score_100');

  container.innerHTML = `
    <div>
      <span class="score-100-badge">Vision Score (0–100): ${score100.text} &nbsp;(Interval: ${score100Interval})</span>
    </div>
    <div class="metric-line">
      Measured acuity score <sup>1</sup> :<br>
      <b>${scoreStr}</b>
    </div>
    <div class="metric-line">
      With confidence interval <sup>2</sup> :<br>
      <span>${intervalStr}</span>
    </div>
    <div style="font-size: 13px; color: #666; margin-bottom: 10px;">
      (${resObj.snellen_feet} &nbsp;|&nbsp; ${resObj.map_logmar.toFixed(2)} logMAR &nbsp;|&nbsp; N = ${resObj.question_index} questions)
    </div>
    <div class="dist-plots-wrap">
      <div class="dist-plots-title">Posterior Distribution — Acuity (arcmins):</div>
      <canvas id="${prefix}DistArcmin" class="result-dist-canvas"></canvas>
      <div class="dist-plots-title" style="margin-top: 6px;">Posterior Distribution — Acuity (logMAR):</div>
      <canvas id="${prefix}DistLogmar" class="result-dist-canvas"></canvas>
    </div>
  `;

  drawArcminsChart(
    document.getElementById(`${prefix}DistArcmin`), 360, 155, resObj.curve_arc_xs, resObj.curve_arc_ys
  );
  drawLogmarChart(
    document.getElementById(`${prefix}DistLogmar`), 360, 155, resObj.curve_log_xs, resObj.curve_log_ys
  );
}

function renderTraceTable(eyeRes) {
  const tbody = document.getElementById('historyTableBody');
  tbody.innerHTML = '';
  ['Left Eye', 'Right Eye'].forEach(eyeName => {
    const r = eyeRes[eyeName];
    if (!r || !r.history) return;
    r.history.forEach(item => {
      const sc = arcminToScore0_100(item.map_k1).text;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><b>${eyeName}</b></td>
        <td>${item.q}</td>
        <td>${item.size_arcmins.toFixed(1)}</td>
        <td>${item.size_logmar.toFixed(1)}</td>
        <td>${item.direction}</td>
        <td>${item.answer}</td>
        <td style="color:${item.correct ? '#16a34a' : '#dc2626'}; font-weight:600;">${item.correct ? 'Correct ✓' : 'Wrong ✗'}</td>
        <td>${item.map_k1.toFixed(1)} arcmin (${item.map_logmar.toFixed(1)} logMAR)</td>
        <td><b>${sc}</b></td>
      `;
      tbody.appendChild(tr);
    });
  });
}

// =========================================================================
// VISION HISTORY OVER TIME (TREND CHART + LOG TABLE)
// =========================================================================

function populateUserFilterDropdown(historyList) {
  const select = document.getElementById('historyUserFilter');
  const prevVal = select.value || 'ALL';
  const users = Array.from(new Set(historyList.map(r => r.user_name || 'Guest')));

  select.innerHTML = `<option value="ALL">All Users (${historyList.length} records)</option>`;
  users.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u;
    opt.innerText = `User: ${u}`;
    select.appendChild(opt);
  });
  if (users.includes(prevVal)) select.value = prevVal;
}

function getFilteredHistory() {
  if (!latestResultsPayload || !latestResultsPayload.vision_history) return [];
  const all = latestResultsPayload.vision_history;
  const filterVal = document.getElementById('historyUserFilter').value;
  if (filterVal === 'ALL') return all;
  return all.filter(r => (r.user_name || 'Guest') === filterVal);
}

function renderVisionHistorySection() {
  const records = getFilteredHistory();
  const tbody = document.getElementById('visionHistoryTableBody');
  tbody.innerHTML = '';

  if (records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="color:#64748b; font-style:italic; padding:14px;">No saved vision history records yet.</td></tr>`;
  } else {
    records.slice().reverse().forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.test_date}</td>
        <td><b>${r.user_name || 'Guest'}</b></td>
        <td>${r.eye}</td>
        <td><span style="background:#eff6ff; color:#1d4ed8; font-weight:700; padding:2px 8px; border-radius:10px;">${r.score_0_100}</span></td>
        <td>${Number(r.map_k1).toFixed(2)}</td>
        <td>${Number(r.map_logmar).toFixed(2)}</td>
        <td>${r.snellen_feet}</td>
        <td>[${Number(r.ci_low).toFixed(1)}, ${Number(r.ci_high).toFixed(1)}]</td>
      `;
      tbody.appendChild(tr);
    });
  }

  drawHistoryTrendChart(records);
}

function drawHistoryTrendChart(records) {
  const canvas = document.getElementById('historyTrendCanvas');
  const W = 810, H = 210;
  const ctx = setupHiDPICanvas(canvas, W, H);

  const padL = 55, padR = 30, padT = 28, padB = 42;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const x0 = padL, y0 = padT + plotH;

  // Y-axis: 0 to 105 (where 105 is labeled "100+")
  const yTicks = [
    { v: 0, lbl: '0' },
    { v: 25, lbl: '25' },
    { v: 50, lbl: '50' },
    { v: 75, lbl: '75' },
    { v: 100, lbl: '100' },
    { v: 105, lbl: '100+' }
  ];

  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  yTicks.forEach(t => {
    const py = y0 - (t.v / 108.0) * plotH;
    ctx.beginPath(); ctx.moveTo(x0, py); ctx.lineTo(x0 + plotW, py); ctx.stroke();
  });

  // Axes
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x0, padT); ctx.lineTo(x0, y0); ctx.lineTo(x0 + plotW, y0); ctx.stroke();

  ctx.fillStyle = '#475569';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'right';
  yTicks.forEach(t => {
    const py = y0 - (t.v / 108.0) * plotH;
    ctx.fillText(t.lbl, x0 - 8, py + 4);
  });

  // Legend
  ctx.textAlign = 'left';
  ctx.font = 'bold 12px sans-serif';
  ctx.fillStyle = '#2563eb';
  ctx.fillText('● Left Eye Score (0–100+)', x0 + 10, 17);
  ctx.fillStyle = '#16a34a';
  ctx.fillText('● Right Eye Score (0–100+)', x0 + 200, 17);

  if (records.length === 0) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = 'italic 13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Complete an exam to see your vision trend over time', x0 + plotW / 2, padT + plotH / 2);
    return;
  }

  // Group points by eye in chronological order
  const n = records.length;
  const xStep = n > 1 ? plotW / (n - 1) : 0;

  ['Left Eye', 'Right Eye'].forEach(eyeName => {
    const color = eyeName === 'Left Eye' ? '#2563eb' : '#16a34a';
    const pts = [];
    records.forEach((r, idx) => {
      if (r.eye === eyeName) {
        const px = n > 1 ? x0 + idx * xStep : x0 + plotW / 2;
        const val = Math.min(105, Math.max(0, Number(r.score_0_100_num || 50)));
        const py = y0 - (val / 108.0) * plotH;
        pts.push({ px, py, lbl: r.score_0_100, date: r.test_date });
      }
    });

    if (pts.length > 1) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      pts.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.px, p.py);
        else ctx.lineTo(p.px, p.py);
      });
      ctx.stroke();
    }

    pts.forEach(p => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.px, p.py, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.font = 'bold 10.5px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(p.lbl, p.px, p.py - 8);
    });
  });

  // Draw X-axis date labels (up to 6 evenly spaced labels)
  ctx.fillStyle = '#475569';
  ctx.font = '10.5px sans-serif';
  ctx.textAlign = 'center';
  const maxLabels = Math.min(6, n);
  const labelStride = Math.max(1, Math.floor(n / maxLabels));
  records.forEach((r, idx) => {
    if (idx % labelStride === 0 || idx === n - 1) {
      const px = n > 1 ? x0 + idx * xStep : x0 + plotW / 2;
      const shortDate = (r.test_date || '').split(' ')[0];
      ctx.fillText(shortDate, px, y0 + 18);
    }
  });
}

async function clearVisionHistory() {
  const res = await fetch('/api/clear_history', { method: 'POST' });
  const data = await res.json();
  if (latestResultsPayload) {
    latestResultsPayload.vision_history = data.vision_history || [];
    populateUserFilterDropdown(latestResultsPayload.vision_history);
    renderVisionHistorySection();
  }
}

function exportHistoryCSV() {
  const records = getFilteredHistory();
  if (records.length === 0) return;
  const headers = ['Date', 'User_Name', 'Eye', 'Score_0_100', 'MAP_Arcmin', 'MAP_LogMAR', 'Snellen_Feet', 'CI_Low_Arcmin', 'CI_High_Arcmin', 'Questions'];
  const rows = records.map(r => [
    `"${r.test_date || ''}"`,
    `"${r.user_name || 'Guest'}"`,
    `"${r.eye || ''}"`,
    `"${r.score_0_100 || ''}"`,
    Number(r.map_k1).toFixed(2),
    Number(r.map_logmar).toFixed(2),
    `"${r.snellen_feet || ''}"`,
    Number(r.ci_low).toFixed(2),
    Number(r.ci_high).toFixed(2),
    r.question_index || 20
  ].join(','));
  const csvContent = [headers.join(','), ...rows].join(String.fromCharCode(10));
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.download = 'StAT_Vision_History_Over_Time.csv';
  link.href = URL.createObjectURL(blob);
  link.click();
}

// =========================================================================
// EXPORT / SAVE RESULTS AS HIGH-RES PNG (WITH USER, DATE, 0-100 SCORE & DISTRIBUTIONS)
// =========================================================================

function saveResultsAsImage() {
  if (!latestResultsPayload || !latestResultsPayload.eye_results) return;
  const unit = document.getElementById('unitSelector').value;
  const eyeRes = latestResultsPayload.eye_results;
  const userName = latestResultsPayload.user_name ? latestResultsPayload.user_name : 'Guest';
  const testDate = latestResultsPayload.test_date || formatCurrentDateTime();

  const W = 960, H = 720;
  const dpr = 2;
  const outCanvas = document.createElement('canvas');
  outCanvas.width = W * dpr;
  outCanvas.height = H * dpr;
  const ctx = outCanvas.getContext('2d');
  ctx.scale(dpr, dpr);

  // Clean White background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 21px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Stanford Acuity Test (StAT) — Vision Results', W / 2, 36);

  ctx.fillStyle = '#475569';
  ctx.font = '14px sans-serif';
  ctx.fillText(`Patient / User: ${userName}   |   Date of Test: ${testDate}`, W / 2, 60);

  // Draw Left Eye Card & Right Eye Card side-by-side
  const cards = [
    { title: 'Left Eye Results', data: eyeRes['Left Eye'], x: 40, prefix: 'left' },
    { title: 'Right Eye Results', data: eyeRes['Right Eye'], x: 500, prefix: 'right' }
  ];

  cards.forEach(c => {
    const cx = c.x, cy = 80, cw = 420, ch = 615;
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(cx, cy, cw, ch);
    ctx.strokeStyle = '#dcdcdc';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(cx, cy, cw, ch);

    ctx.fillStyle = '#222222';
    ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(c.title, cx + cw / 2, cy + 30);

    if (!c.data) {
      ctx.fillStyle = '#666666';
      ctx.font = 'italic 17px sans-serif';
      ctx.fillText('No results yet', cx + cw / 2, cy + 120);
      return;
    }

    const sc100 = arcminToScore0_100(c.data.map_k1).text;
    const sc100Int = formatIntervalByUnit(c.data.ci_low, c.data.ci_high, 'score_100').replace(/&nbsp;/g, ' ');
    const scoreStr = formatAcuityByUnit(c.data.map_k1, unit).replace(/&nbsp;/g, ' ');
    const intervalStr = formatIntervalByUnit(c.data.ci_low, c.data.ci_high, unit).replace(/&nbsp;/g, ' ');

    ctx.fillStyle = '#1d4ed8';
    ctx.font = 'bold 15px sans-serif';
    ctx.fillText(`Vision Score (0–100): ${sc100}  (Interval: ${sc100Int})`, cx + cw / 2, cy + 56);

    ctx.fillStyle = '#333333';
    ctx.font = '15.5px sans-serif';
    ctx.fillText('Measured acuity score ¹ :', cx + cw / 2, cy + 84);
    ctx.font = 'bold 18px sans-serif';
    ctx.fillText(scoreStr, cx + cw / 2, cy + 106);

    ctx.font = '15.5px sans-serif';
    ctx.fillText('With confidence interval ² :', cx + cw / 2, cy + 134);
    ctx.fillText(intervalStr, cx + cw / 2, cy + 156);

    ctx.fillStyle = '#64748b';
    ctx.font = '12.5px sans-serif';
    ctx.fillText(`(${c.data.snellen_feet} | ${c.data.map_logmar.toFixed(2)} logMAR | N = ${c.data.question_index} questions)`, cx + cw / 2, cy + 180);

    const arcCanvas = document.getElementById(`${c.prefix}DistArcmin`);
    const logCanvas = document.getElementById(`${c.prefix}DistLogmar`);
    if (arcCanvas && logCanvas) {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(cx + 16, cy + 194, cw - 32, 405);
      ctx.strokeStyle = '#e5e7eb';
      ctx.strokeRect(cx + 16, cy + 194, cw - 32, 405);

      ctx.fillStyle = '#374151';
      ctx.font = 'bold 13px sans-serif';
      ctx.fillText('Posterior Distribution — Acuity (arcmins):', cx + cw / 2, cy + 214);
      ctx.drawImage(arcCanvas, cx + 30, cy + 220, 360, 155);

      ctx.fillText('Posterior Distribution — Acuity (logMAR):', cx + cw / 2, cy + 398);
      ctx.drawImage(logCanvas, cx + 30, cy + 404, 360, 155);
    }
  });

  const safeUser = userName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const safeDate = testDate.split(' ')[0];
  const link = document.createElement('a');
  link.download = `StAT_Vision_Results_${safeUser}_${safeDate}.png`;
  link.href = outCanvas.toDataURL('image/png');
  link.click();
}

function saveResultsAsJSON() {
  if (!latestResultsPayload) return;
  const exportObj = {
    user_name: latestResultsPayload.user_name || 'Guest',
    test_date: latestResultsPayload.test_date,
    current_session_results: latestResultsPayload.eye_results,
    vision_history_over_time: latestResultsPayload.vision_history || []
  };
  const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.download = 'StAT_Vision_Results_Data.json';
  link.href = URL.createObjectURL(blob);
  link.click();
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('testDateInput').value = formatCurrentDateTime();
  setDiagonalPreset(15.6, document.getElementById('defaultPresetBtn'));
});
</script>
</body>
</html>
"""


def snapshot_current_eye_result():
    pred_k1 = stat.get_predicted_acuity(SESSION["belief"])
    map_k1, map_logmar = stat.get_map_acuity_logmar(SESSION["belief"])
    conf = stat.get_confidence_within_10_percent(SESSION["belief"])
    ci_low, ci_high = stat.get_credible_interval(SESSION["belief"], 0.95)
    metrics = stat.arcmins_to_clinical_metrics(map_k1)
    arc_xs, arc_ys = stat.get_smooth_posterior_curve_arcmins(SESSION["belief"], max_x=12.0, num_points=120)
    log_xs, log_ys = stat.get_smooth_posterior_curve_logmar(SESSION["belief"], min_logmar=-0.8, max_logmar=1.25, num_points=100)

    return {
        "user_name": SESSION["user_name"] or "Guest",
        "test_date": SESSION["test_date"],
        "eye": SESSION["selected_eye"],
        "question_index": SESSION["question_index"],
        "predicted_k1": pred_k1,
        "map_k1": map_k1,
        "map_logmar": map_logmar,
        "score_0_100": metrics["score_0_100"],
        "score_0_100_num": metrics["score_0_100_num"],
        "snellen_feet": metrics["snellen_feet"],
        "snellen_meters": metrics["snellen_meters"],
        "confidence": conf,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "curve_arc_xs": arc_xs,
        "curve_arc_ys": arc_ys,
        "curve_log_xs": log_xs,
        "curve_log_ys": log_ys,
        "history": list(SESSION["history"])
    }


def build_state_payload(finished=False, ask_continue=False):
    pred_k1 = stat.get_predicted_acuity(SESSION["belief"])
    map_k1, map_logmar = stat.get_map_acuity_logmar(SESSION["belief"])
    conf = stat.get_confidence_within_10_percent(SESSION["belief"])
    ci_low, ci_high = stat.get_credible_interval(SESSION["belief"], 0.95)
    metrics = stat.arcmins_to_clinical_metrics(map_k1)

    arc_xs, arc_ys = stat.get_smooth_posterior_curve_arcmins(SESSION["belief"], max_x=12.0, num_points=120)
    log_xs, log_ys = stat.get_smooth_posterior_curve_logmar(SESSION["belief"], min_logmar=-0.8, max_logmar=1.25, num_points=100)

    letter_px = stat.arcmins_to_pixels(
        SESSION["current_size_arcmins"], SESSION["distance_cm"], SESSION["pixels_per_mm"]
    )
    progress_pct = min(100, int(round((SESSION["question_index"] / float(max(1, SESSION["max_questions"]))) * 100)))

    return {
        "finished": finished,
        "ask_continue": ask_continue,
        "user_name": SESSION["user_name"],
        "test_date": SESSION["test_date"],
        "selected_eye": SESSION["selected_eye"],
        "question_index": SESSION["question_index"],
        "max_questions": SESSION["max_questions"],
        "progress_pct": progress_pct,
        "current_size_arcmins": SESSION["current_size_arcmins"],
        "current_direction": SESSION["current_direction"],
        "letter_height_px": letter_px,
        "predicted_k1": pred_k1,
        "map_k1": map_k1,
        "map_logmar": map_logmar,
        "score_0_100": metrics["score_0_100"],
        "score_0_100_num": metrics["score_0_100_num"],
        "snellen_feet": metrics["snellen_feet"],
        "snellen_meters": metrics["snellen_meters"],
        "logmar": metrics["logmar"],
        "confidence": conf,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "curve_arc_xs": arc_xs,
        "curve_arc_ys": arc_ys,
        "curve_log_xs": log_xs,
        "curve_log_ys": log_ys,
        "history": SESSION["history"],
        "eye_results": SESSION["eye_results"],
        "vision_history": stat.load_vision_history()
    }


class StATHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/measure") or self.path.startswith("/index"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path.startswith("/favicon"):
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if self.path == "/api/start":
            SESSION["user_name"] = str(body.get("user_name", "")).strip()
            SESSION["test_date"] = str(body.get("test_date", "")).strip() or datetime.now().strftime("%Y-%m-%d %H:%M")
            SESSION["distance_cm"] = float(body.get("distance_cm", 100.0))
            SESSION["pixels_per_mm"] = float(body.get("pixels_per_mm", 3.74))
            SESSION["selected_eye"] = body.get("selected_eye", "Left Eye")
            SESSION["exam_mode"] = body.get("exam_mode", "standard_20")
            SESSION["max_questions"] = 20 if SESSION["exam_mode"] == "standard_20" else 60
            SESSION["belief"] = stat.get_prior_belief()
            SESSION["question_index"] = 0
            SESSION["history"] = []

            SESSION["current_size_arcmins"] = stat.choose_next_letter_size(SESSION["belief"])
            SESSION["current_direction"] = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])

            payload = build_state_payload(finished=False, ask_continue=False)
            self._send_json(payload)

        elif self.path == "/api/answer":
            user_answer = body.get("answer", "")
            is_correct = (user_answer == SESSION["current_direction"])

            SESSION["belief"] = stat.update_belief(
                SESSION["belief"],
                {"size": SESSION["current_size_arcmins"], "correct": is_correct}
            )
            SESSION["question_index"] += 1

            map_k1, map_logmar = stat.get_map_acuity_logmar(SESSION["belief"])
            ci_low, ci_high = stat.get_credible_interval(SESSION["belief"], 0.95)
            conf = stat.get_confidence_within_10_percent(SESSION["belief"])

            SESSION["history"].append({
                "q": SESSION["question_index"],
                "size_arcmins": SESSION["current_size_arcmins"],
                "size_logmar": math.log10(SESSION["current_size_arcmins"]),
                "direction": SESSION["current_direction"],
                "answer": user_answer,
                "correct": is_correct,
                "map_k1": map_k1,
                "map_logmar": map_logmar,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "confidence": conf
            })

            reached_batch_limit = (SESSION["question_index"] >= SESSION["max_questions"])
            stat_star_done = (
                SESSION["exam_mode"] == "stat_star" and SESSION["question_index"] >= 5 and conf >= 0.95
            )

            if reached_batch_limit or stat_star_done:
                payload = build_state_payload(finished=False, ask_continue=True)
                self._send_json(payload)
            else:
                SESSION["current_size_arcmins"] = stat.choose_next_letter_size(SESSION["belief"])
                SESSION["current_direction"] = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
                payload = build_state_payload(finished=False, ask_continue=False)
                self._send_json(payload)

        elif self.path == "/api/continue":
            extra = int(body.get("extra_questions", 10))
            SESSION["max_questions"] = SESSION["question_index"] + max(1, extra)
            SESSION["current_size_arcmins"] = stat.choose_next_letter_size(SESSION["belief"])
            SESSION["current_direction"] = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            payload = build_state_payload(finished=False, ask_continue=False)
            self._send_json(payload)

        elif self.path == "/api/finish":
            eye_key = SESSION["selected_eye"]
            if eye_key not in ("Left Eye", "Right Eye"):
                eye_key = "Left Eye"
            snap = snapshot_current_eye_result()
            SESSION["eye_results"][eye_key] = snap

            # Append to persistent vision_history.json for tracking over time
            stat.append_vision_history_record({
                "user_name": snap["user_name"],
                "test_date": snap["test_date"],
                "eye": snap["eye"],
                "score_0_100": snap["score_0_100"],
                "score_0_100_num": snap["score_0_100_num"],
                "map_k1": round(snap["map_k1"], 3),
                "map_logmar": round(snap["map_logmar"], 3),
                "snellen_feet": snap["snellen_feet"],
                "ci_low": round(snap["ci_low"], 2),
                "ci_high": round(snap["ci_high"], 2),
                "question_index": snap["question_index"]
            })

            payload = build_state_payload(finished=True, ask_continue=False)
            self._send_json(payload)

        elif self.path == "/api/clear_history":
            stat.clear_vision_history()
            self._send_json({"vision_history": []})

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def find_available_port(start_port=8000, max_tries=20):
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port


if __name__ == "__main__":
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}/measure?v=8"
    print("=================================================================")
    print("Stanford Acuity Test (StAT) v8 Web Server is running at:")
    print(f"    {url}")
    print("Opening in your browser automatically... (Press Ctrl+C to stop)")
    print("=================================================================")
    server = ThreadingHTTPServer(("127.0.0.1", port), StATHTTPRequestHandler)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
