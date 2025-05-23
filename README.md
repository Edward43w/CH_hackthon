
# 中文語音助手 (Chinese Voice Assistant)

一個基於AWS服務的中文語音交互助手，使用先進的語音識別和自然語言處理技術，提供智能對話體驗。

## ✨ 功能特點

- 🎯 熱詞喚醒：說"你好"來喚醒助手
- 🗣️ 高精度語音識別：使用AWS Whisper模型實現中文語音識別
- 🤖 智能命令分類：自動分類為聊天、查詢和行動三種類型
- 🔊 自然語音合成：使用AWS Polly實現流暢的中文語音輸出
- 🎛️ 語音控制：支持"停"、"慢一點"、"快一點"、"恢復正常"等語音控制指令
- 🎮 連續對話：說"再見"結束對話模式，返回熱詞監聽

## 🛠️ 技術架構

### 前端
- React框架
- Web Audio API用於音頻錄製
- 語音合成API (SpeechSynthesis)
- Axios用於API通信

### 後端
- Flask Web服務
- AWS Whisper用於語音識別
- AWS Polly用於語音合成
- AWS Bedrock代理用於命令分類和回應生成
- 執行緒處理用於非阻塞命令處理

## 📝 系統流程

1. **熱詞喚醒階段**：
   - 系統監聽用戶語音，偵測熱詞"你好"
   - 一旦檢測到熱詞，進入命令監聽模式

2. **命令處理階段**：
   - 收集用戶語音命令
   - 使用Whisper進行高精度轉錄
   - 將轉錄文本分類為聊天、查詢或行動命令
   - 生成相應回應

3. **回應階段**：
   - 使用Polly生成語音回應
   - 在前端播放語音
   - 等待用戶進一步互動

## 🚀 安裝和設置

### 前提條件
- Node.js 14+ 和npm
- Python 3.8+
- AWS帳戶與相關服務訪問權限

### 後端設置
```bash
# 克隆儲存庫
git clone https://github.com/yourusername/ch-voice-assistant.git
cd ch-voice-assistant

# 設置Python虛擬環境
python -m venv venv
source venv/bin/activate  # Windows使用: venv\Scripts\activate

# 安裝後端依賴
cd backend
pip install -r requirements.txt

# 配置AWS憑證
# 在backend/config/.env中添加:
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
# AWS_REGION=your_region
# SAGEMAKER_ENDPOINT_NAME=your_endpoint_name
```

### 前端設置
```bash
# 安裝前端依賴
cd ../frontend
npm install

# 啟動開發服務器
npm run dev
```

### 啟動應用
```bash
# 啟動後端服務 (在backend目錄)
python app.py

# 在瀏覽器訪問
# http://localhost:5173 (或Vite顯示的端口)
```

## 📊 使用方法

1. 打開應用後，點擊螢幕以啟用麥克風
2. 說"你好"來喚醒語音助手
3. 當系統顯示"我在聽"時，說出您的問題或命令
4. 系統會通過文字和語音回應您的請求
5. 說"再見"結束當前對話，返回待機模式

### 語音控制命令
- "停" - 停止當前語音播放
- "慢一點" - 降低語音播放速度
- "快一點" - 提高語音播放速度
- "恢復正常" - 重置為默認語音速度

## 💡 開發者筆記

- 前端使用MediaRecorder API錄製音頻，發送到後端進行處理
- 後端使用AWS Whisper模型進行語音識別，精確度高於Web Speech API
- 命令分類使用AWS Bedrock代理實現，基於參考示例進行分類
- 後端使用多執行緒處理音頻和命令，避免阻塞主線程

## 📜 許可證

MIT

---

© 2025 語音助手專案團隊
