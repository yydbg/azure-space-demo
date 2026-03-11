import azure.functions as func
import requests
import json
import logging
import os

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="getStarlink")
def getStarlink(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('收到請求，準備載入 Starlink 軌道資料...')

    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    lines = []
    source = "線上即時 (CelesTrak)"

    # 第一階段：嘗試從線上 API 抓取最新資料
    try:
        logging.info('嘗試連線至 CelesTrak...')
        # 設定 timeout 為 5 秒，如果 5 秒內連不上就果斷放棄，進入備援機制
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        
    except Exception as e:
        # 第二階段：線上抓取失敗，啟動本地檔案備援機制
        logging.warning(f"連線 CelesTrak 失敗 ({e})。正在切換至本地 starlink.txt 備援檔案...")
        source = "本地備援檔案 (starlink.txt)"
        
        try:
            # 取得當前程式碼所在的資料夾路徑，並讀取 starlink.txt
            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(dir_path, 'starlink.txt')
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                
        except FileNotFoundError:
            return func.HttpResponse(
                "嚴重錯誤：線上 API 無法連線，且找不到本地的 starlink.txt 備援檔案。", 
                status_code=404
            )
        except Exception as local_e:
            return func.HttpResponse(
                f"讀取本地備援檔案時發生錯誤: {local_e}", 
                status_code=500
            )

    # 第三階段：解析資料 (無論是從線上還是本地來的)
    satellites = []
    
    # 限制載入數量以防瀏覽器卡頓 (3000 行 = 1000 顆衛星)，如果你電腦夠力可以把這行改成 limit = len(lines)
    limit = min(len(lines), 3000) 
    
    for i in range(0, limit, 3):
        if i + 2 < len(lines):
            satellites.append({
                "name": lines[i].strip(),
                "tle1": lines[i+1].strip(),
                "tle2": lines[i+2].strip()
            })
            
    logging.info(f"成功載入 {len(satellites)} 顆衛星資料。資料來源：{source}")
    
    return func.HttpResponse(
        body=json.dumps(satellites), 
        mimetype="application/json", 
        status_code=200
    )