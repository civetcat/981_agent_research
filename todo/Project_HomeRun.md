# Project HomeRun: 高速影像 AI 動作分析系統

## 📝 專案描述
利用 1080p @ 240fps 高速影像實作自動化動作監測系統，提供即時慢動作回放與姿勢修正建議，應用於棒球打擊與投球。

## 🎯 階段目標
- **短期 (MVP)**: 實作影片播放器與基礎揮棒偵測（背景差分法）。
- **中期 (系統整合)**: 導入 MediaPipe/YOLO 骨架分析，達成「打完即看」低延遲回放。
- **長期 (硬體部署)**: 封裝至 Jetson Orin Nano 與工業鏡頭，製作 3D 列印外殼。

## 📊 當前狀態
- [進行中] MVP 開發：使用 OpenCV 處理 Action 6 預錄影片。

## 🛠 技術棧
- Python, OpenCV, MediaPipe
- Hardware: DJI Action 6, Jetson Orin Nano, P1S (外殼製作)
