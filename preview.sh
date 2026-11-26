#!/bin/bash
# 桌機用：依 content.md 重新產生網站，並在 localhost:8848 開預覽（跟上線後一樣可以切換頁面）
# 用法：VS Code（Remote-SSH 連 desktop）開這個資料夾，在終端機執行 ./preview.sh
#       VS Code 會自動把 8848 轉到 Mac，在 Mac 瀏覽器打開 http://localhost:8848/
# 注意：8765 是 Mac 上論文圖書館在用的，不要改成 8765
cd "$(dirname "$0")"
python3 build.py || { echo '產生失敗，看上面的錯誤訊息'; exit 1; }
PORT=8848
URL="http://localhost:$PORT/"
if python3 -c "import sys,urllib.request as u; sys.exit(b'generated-by-build.py' not in u.urlopen('$URL', timeout=2).read())" 2>/dev/null; then
  echo "預覽已經在跑，瀏覽器重新整理就好：$URL"
  exit 0
fi
if ss -ltn "sport = :$PORT" | grep -q LISTEN; then
  echo "連接埠 $PORT 被別的程式佔用了，請告訴 Claude 換一個"
  exit 1
fi
echo
echo "預覽網址：$URL"
echo '改完 content.md 存檔後，在另一個終端機再跑一次 ./preview.sh（或直接重新整理）；Control+C 停止預覽。'
exec python3 -m http.server "$PORT" --bind 127.0.0.1
