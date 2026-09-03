#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: Google Drive 更新追蹤工具
description: 分析指定的 Google Drive 目錄，查詢在特定日期之後被修改或建立的檔案，並列出其名稱、修改時間與連結。
category: dulan-ai-hub
dependencies: google-api-python-client, google-auth-oauthlib, google-auth-httplib2, google-auth
"""

import os
import sys
from datetime import datetime, timedelta, timezone
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_gdrive_service(credentials_path="credentials.json", token_path="token.json"):
    """
    取得 Google Drive API 服務實例。
    支援 token.json 快取、credentials.json 交互式認證，以及 Application Default Credentials (ADC) 備用方案。
    """
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    creds = None
    
    # 1. 嘗試載入 token.json
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception:
            creds = None
        
    # 2. 如果沒有 token.json 或無效，且有 credentials.json，進行 InstalledAppFlow 認證
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
                
        if not creds:
            if os.path.exists(credentials_path):
                try:
                    from google_auth_oauthlib.flow import InstalledAppFlow
                except ImportError:
                    raise ImportError(
                        "偵測到有 credentials.json，需要進行 OAuth 授權流程，"
                        "但系統尚未安裝 'google-auth-oauthlib' 套件。\n"
                        "請執行 'pip install google-auth-oauthlib google-auth-httplib2' 進行安裝。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
                creds = flow.run_local_server(port=0)
                # 存下 token 供下次使用
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                # 3. 嘗試使用 Application Default Credentials (ADC)
                try:
                    creds, project = google.auth.default(scopes=scopes)
                except Exception as e:
                    raise RuntimeError(
                        f"無法取得 Google API 憑證。\n"
                        f"請在專案中提供 '{credentials_path}' 以進行 OAuth 認證，\n"
                        f"或是在終端機中設定 Google Cloud Application Default Credentials (ADC)。\n"
                        f"詳細錯誤訊息：{e}"
                    )
                
    return build('drive', 'v3', credentials=creds)

def parse_since_param(since_val):
    """
    將 since 參數轉換成 RFC 3339 格式的 UTC 時間字串。
    支援：天數 (如 '3')、日期 (如 '2026-07-08') 或完整的 ISO-8601 時間字串。
    """
    # 1. 嘗試解析天數 (整數)
    try:
        days = int(since_val)
        dt = datetime.now(timezone.utc) - timedelta(days=days)
        return dt.isoformat().replace('+00:00', 'Z')
    except ValueError:
        pass
        
    # 2. 嘗試解析 YYYY-MM-DD
    try:
        dt = datetime.strptime(since_val, "%Y-%m-%d")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace('+00:00', 'Z')
    except ValueError:
        pass

    # 3. 嘗試解析完整的 ISO 格式
    try:
        if since_val.endswith('Z'):
            # 確保格式正確，做簡單驗證
            datetime.strptime(since_val.replace('Z', '+00:00'), "%Y-%m-%dT%H:%M:%S%z")
            return since_val
        dt = datetime.fromisoformat(since_val)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except ValueError:
        raise ValueError(
            f"無法解析的日期時間格式: '{since_val}'。\n"
            f"支援格式：\n"
            f"  - 天數 (如: '3' 代表 3 天內)\n"
            f"  - 日期 (如: '2026-07-08')\n"
            f"  - ISO 8601 (如: '2026-07-08T12:00:00Z')"
        )

def track_gdrive_updates(folder_id, since, credentials_path="credentials.json", token_path="token.json"):
    """
    查詢指定 Google Drive 資料夾內在 since 時間之後有更新的檔案。
    """
    if not folder_id:
        raise ValueError("必須提供 folder_id")
        
    service = get_gdrive_service(credentials_path, token_path)
    since_rfc3339 = parse_since_param(since)
    
    # 查詢 parent 是 folder_id、非垃圾桶且修改時間大於 since 的檔案
    query = f"'{folder_id}' in parents and modifiedTime > '{since_rfc3339}' and trashed = false"
    
    files = []
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, modifiedTime, webViewLink, mimeType)',
            orderBy='modifiedTime desc',
            pageToken=page_token
        ).execute()
        
        items = results.get('files', [])
        files.extend(items)
        
        page_token = results.get('nextPageToken', None)
        if not page_token:
            break
            
    return {
        "since": since_rfc3339,
        "folder_id": folder_id,
        "files": files
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Drive 資料夾異動追蹤工具")
    parser.add_argument(
        "-f", "--folder-id",
        default="1IrM_8cMWQZb-oeFCSHJ4qMZ5pVihv2fs",
        help="要分析的 Google Drive 資料夾 ID (預設為學員筆記目錄)"
    )
    parser.add_argument(
        "-s", "--since",
        required=True,
        help="篩選在此時間點之後的更新。可傳入天數 (如 3)、日期 (如 2026-07-08) 或 ISO 8601 時間字串"
    )
    parser.add_argument(
        "-c", "--credentials",
        default="credentials.json",
        help="Google Client Secrets OAuth 憑證金鑰檔路徑 (預設為 credentials.json)"
    )
    parser.add_argument(
        "-t", "--token",
        default="token.json",
        help="OAuth 授權後的存取權杖檔路徑 (預設為 token.json)"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"正在連線 Google Drive API 並分析資料夾 [{args.folder_id}]...")
        result = track_gdrive_updates(
            folder_id=args.folder_id,
            since=args.since,
            credentials_path=args.credentials,
            token_path=args.token
        )
        
        files = result["files"]
        since_time = result["since"]
        
        print(f"\n篩選基準時間 (UTC)：{since_time}")
        print(f"共尋找到 {len(files)} 個在此時間後更新的檔案：\n")
        
        if not files:
            print("\033[93m沒有找到任何符合篩選時間的異動檔案。\033[0m")
        else:
            for idx, file_info in enumerate(files, 1):
                name = file_info.get("name")
                mod_time = file_info.get("modifiedTime")
                link = file_info.get("webViewLink")
                print(f"{idx}. \033[92m{name}\033[0m")
                print(f"   修改時間 (UTC): {mod_time}")
                print(f"   連結: {link}")
                print("-" * 50)
                
    except Exception as e:
        print(f"\033[91m[錯誤] 執行失敗: {e}\033[0m", file=sys.stderr)
        sys.exit(1)
