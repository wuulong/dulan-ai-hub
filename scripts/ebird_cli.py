#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: ebird_cli.py
title: eBird 在地鳥類生態觀測與即時鳥況 CLI
description: 符合 CGS v2.1 規範的 eBird API v2.0 命令列工具。與 inat_cli 設定檔 (places.json) 100% 相容，支援都蘭即時鳥況檢索、歷史日期區間查詢 (historic)、熱門賞鳥點探勘、稀有鳥種快訊、清單觀測者下鑽 (checklist)、個人歷史觀察 CSV 空間與日期篩選 (user-csv) 以及旅行足跡時間軸 (trip)。
category: ecology
spec: @dulan-ai-hub/topics/ebird/ebird-dulan-cli-spec.md
manual: @dulan-ai-hub/manuals/ebird_cli.md
dependencies: urllib, json, csv
cgs_version: 2.1
"""

import os
import sys
import csv
import json
import time
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# 顯式宣告 CGS 規格版號
__cli_spec_version__ = "2.1"

# 定錨至 dulan-ai-hub 專案根目錄
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_ROOT = PROJECT_ROOT
SPEC_PATH = os.path.join(PROJECT_ROOT, "topics/ebird/ebird-dulan-cli-spec.md")
MANUAL_PATH = os.path.join(PROJECT_ROOT, "manuals/ebird_cli.md")
DEFAULT_PLACES_PATH = os.path.join(PROJECT_ROOT, "data/ecology/places.json")
DEFAULT_BIRDS_PATH = os.path.join(PROJECT_ROOT, "data/ecology/dulan_birds.json")
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache/ebird")

_log_file_handle = None

def init_log_file(log_file_path: Optional[str] = None):
    """初始化 --log-file 目錄與檔案 File Handle"""
    global _log_file_handle
    if not log_file_path:
        return
    if log_file_path == "AUTO":
        log_dir = os.path.join(WORKSPACE_ROOT, "tmp", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(log_dir, f"ebird_cli_{timestamp}.log")
    else:
        log_dir = os.path.dirname(os.path.abspath(log_file_path))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    try:
        _log_file_handle = open(log_file_path, "a", encoding="utf-8")
        print(f"ℹ️ [INFO] Log 已自動同步記錄至: {log_file_path}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ [WARN] 無法開啟 Log 檔案 ({log_file_path}): {e}", file=sys.stderr)

def log_msg(level: str, message: str, verbose: bool = False, json_mode: bool = False):
    """CGS v2.0 統一結構化 Log 輸出函式 (走 sys.stderr)"""
    if level.upper() == "DEBUG" and not verbose:
        return

    if json_mode:
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level.upper(),
            "script": "ebird_cli.py",
            "message": message
        }
        formatted_str = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
    else:
        prefix_map = {
            "INFO": "ℹ️ [INFO] ",
            "WARN": "⚠️ [WARN] ",
            "ERROR": "❌ [ERROR] ",
            "DEBUG": "🔍 [DEBUG] "
        }
        prefix = prefix_map.get(level.upper(), "")
        formatted_str = f"{prefix}{message}"

    print(formatted_str, file=sys.stderr)
    if _log_file_handle:
        _log_file_handle.write(formatted_str + "\n")
        _log_file_handle.flush()

def show_manual(open_file: bool = False):
    """顯示或喚醒閱讀器開啟說明書 (CGS Pillar 8)"""
    abs_manual_path = os.path.join(WORKSPACE_ROOT, MANUAL_PATH)
    if not os.path.exists(abs_manual_path):
        print(f"⚠️ 手冊檔案不存在: {abs_manual_path}", file=sys.stderr)
        return
    if open_file:
        try:
            subprocess.run(["open", abs_manual_path], check=False)
            print(f"ℹ️ [INFO] 已開啟手冊: {abs_manual_path}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 無法開啟手冊: {e}", file=sys.stderr)
    else:
        with open(abs_manual_path, "r", encoding="utf-8", errors="ignore") as f:
            print(f.read())

def get_schema() -> Dict[str, Any]:
    """回傳 CGS v2.0 規範之自我描述 Schema"""
    return {
        "domain": "ebird",
        "cgs_version": "2.0",
        "script": "scripts/gis/ebird_cli.py",
        "description": "eBird 在地鳥類生態觀測與即時鳥況 CLI，支援近期鳥況、歷史日期查詢、熱門鳥點探勘、稀有快訊、清單下鑽與個人歷史 CSV 分析",
        "commands": {
            "recent": {
                "description": "查詢指定地點近期（1~30天）即時鳥況觀察紀錄（支援 --user 觀察者過濾）",
                "args": ["--place", "--place-config", "--back", "--user", "-n/--limit"]
            },
            "historic": {
                "description": "查詢指定歷史日期或日期區間（如 2026-04-13 到 2026-04-26）落在該地區的鳥況與觀察紀錄",
                "args": ["--date", "--end-date", "--place", "--place-config", "--user", "-n/--limit"]
            },
            "hotspots": {
                "description": "探勘指定地點周邊經官方認證的熱門賞鳥點與記錄鳥種數",
                "args": ["--place", "--place-config", "-n/--limit"]
            },
            "notable": {
                "description": "查詢指定地點近期罕見或稀有特有鳥種目擊快訊",
                "args": ["--place", "--place-config", "--back"]
            },
            "match": {
                "description": "比對關心鳥類名錄（如都蘭 12 種指標鳥）近期在當地的目擊命中率與最新時間地點",
                "args": ["--place", "--bird-file", "--back", "--user"]
            },
            "checklist": {
                "description": "依 Submission ID (subId) 下鑽查詢該筆清單的觀察者名稱、時間、地點與完整目擊鳥種",
                "args": ["sub_id"]
            },
            "user-csv": {
                "description": "匯入個人歷史觀察 CSV (MyEBirdData.csv)，支援空間過濾、日期區間過濾與都蘭指標鳥自動對照比對",
                "args": ["file", "--place", "--start-date", "--end-date", "--bird-file"]
            },
            "trip": {
                "description": "匯入個人 CSV 分析指定日期區間內的旅行賞鳥足跡時間軸 (Trip Summary)",
                "args": ["file", "--start-date", "--end-date"]
            },
            "export": {
                "description": "匯出近期鳥類觀測點為 GeoJSON 或 CSV 格式",
                "args": ["--place", "--format", "-o/--output"]
            },
            "schema": {
                "description": "輸出此 CLI 工具之自我描述 JSON Schema"
            }
        }
    }

def get_api_key(cli_key: Optional[str] = None) -> Optional[str]:
    """取得 eBird API Token (優先順序: CLI 參數 -> 環境變數 -> 本地憑證檔)"""
    if cli_key:
        return cli_key.strip()
    env_key = os.environ.get("EBIRD_API_KEY")
    if env_key:
        return env_key.strip()
    home_key_file = os.path.expanduser("~/.ebird_api_key")
    if os.path.exists(home_key_file):
        try:
            with open(home_key_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    env_file = os.path.join(WORKSPACE_ROOT, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("EBIRD_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None

class EbirdClient:
    """eBird API v2.0 客戶端 (含 Token 注入與本機快取保護)"""
    BASE_URL = "https://api.ebird.org/v2"

    def __init__(self, api_key: Optional[str], use_cache: bool = True,
                 cache_dir: str = DEFAULT_CACHE_DIR, verbose: bool = False):
        self.api_key = api_key
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.verbose = verbose
        if self.use_cache:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, endpoint: str, params: Dict[str, Any]) -> str:
        key_str = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
        hash_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, expire_hours: int = 2) -> Any:
        if not self.api_key:
            raise ValueError("未偵測到 eBird API Key！請設定環境變數 export EBIRD_API_KEY='your_key' 或傳入 --api-key 旗標。可至 https://ebird.org/api/keygen 免費申請。")

        params = params or {}
        cache_path = self._get_cache_path(endpoint, params) if self.use_cache else None

        if cache_path and os.path.exists(cache_path):
            file_mtime = os.path.getmtime(cache_path)
            if (time.time() - file_mtime) < (expire_hours * 3600):
                log_msg("DEBUG", f"命中本機快取: {cache_path}", verbose=self.verbose)
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        query_string = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/{endpoint}"
        if query_string:
            url = f"{url}?{query_string}"

        log_msg("DEBUG", f"發送 HTTP 請求: {url}", verbose=self.verbose)
        req = urllib.request.Request(
            url,
            headers={
                "X-eBirdApiToken": self.api_key,
                "User-Agent": "bmad-pa-ebird-cli/2.0 (Taiwan locale; respectful-tool)"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if cache_path:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                return data
        except urllib.error.HTTPError as e:
            err_msg = f"eBird API HTTP 錯誤 ({e.code}): {e.reason}"
            if e.code == 403 or e.code == 401:
                err_msg += " (請檢查 API Token 是否有效)"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e
        except Exception as e:
            err_msg = f"連線異常: {str(e)}"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算球面大圓距離 (公里)"""
    from math import radians, cos, sin, asin, sqrt
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return 6371.0 * c

def load_place_config(place_key: Optional[str] = None, place_config_path: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """載入與 inat_cli 100% 相容的空間設定檔"""
    path = place_config_path or DEFAULT_PLACES_PATH
    if not os.path.exists(path):
        return None, {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_key = place_key or data.get("default", "dulan")
    if target_key.lower() in ("any", "all", "none"):
        return target_key, {}

    places = data.get("places", {})
    if target_key not in places:
        raise ValueError(f"區域 key '{target_key}' 不存在於 {path} 中 (可用: {list(places.keys())})")
    return target_key, places[target_key]

def load_birds_config(birds_path: Optional[str] = None) -> Dict[str, Any]:
    """載入關心鳥類名錄設定檔"""
    path = birds_path or DEFAULT_BIRDS_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到鳥類名錄設定檔: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_geo_params(place_info: Dict[str, Any], lat_arg: Optional[float] = None,
                   lng_arg: Optional[float] = None, dist_arg: Optional[float] = None) -> Tuple[float, float, float]:
    """取得經緯度與半徑距離 (公里)"""
    if lat_arg is not None and lng_arg is not None:
        dist = dist_arg if dist_arg is not None else 10.0
        return lat_arg, lng_arg, dist

    if "center" in place_info:
        center = place_info["center"]
        return float(center.get("lat", 22.875)), float(center.get("lng", 121.21)), float(center.get("radius_km", 8.0))
    elif "bbox" in place_info:
        bbox = place_info["bbox"]
        c_lat = (bbox["nelat"] + bbox["swlat"]) / 2.0
        c_lng = (bbox["nelng"] + bbox["swlng"]) / 2.0
        return c_lat, c_lng, 10.0
    return 22.875, 121.21, 8.0

# ==================== CLI 子命令核心邏輯 ====================

def cmd_recent(args, client: EbirdClient):
    """查詢指定地點近期鳥況 (支援 --user 觀察者過濾)"""
    limit_val = getattr(args, "limit", 20)
    back_days = getattr(args, "back", 14)
    filter_user = getattr(args, "user", None)
    _, place_info = load_place_config(args.place, args.place_config)
    lat, lng, dist = get_geo_params(place_info, args.lat, args.lng, args.radius)

    params = {
        "lat": lat,
        "lng": lng,
        "dist": int(dist),
        "back": min(max(back_days, 1), 30),
        "sppLocale": "zh_TW"
    }

    log_msg("INFO", f"正在向 eBird API 檢索近期鳥況 (中心: {lat:.4f},{lng:.4f}, 半徑: {dist}km, 回溯: {back_days}天)...", verbose=args.verbose)
    records = client.request("data/obs/geo/recent", params)

    # 若指定 --user，進行清單觀察者下鑽過濾
    if filter_user:
        log_msg("INFO", f"正在過濾特定觀察者: '{filter_user}'...", verbose=args.verbose)
        filtered_records = []
        user_cache = {}
        for r in records:
            sid = r.get("subId")
            if not sid:
                continue
            if sid not in user_cache:
                try:
                    chk = client.request(f"product/checklist/view/{sid}")
                    user_cache[sid] = chk.get("userDisplayName", "")
                except Exception:
                    user_cache[sid] = ""
            obs_user = user_cache[sid]
            if filter_user.lower() in obs_user.lower():
                r["observer"] = obs_user
                filtered_records.append(r)
        records = filtered_records

    compact_records = []
    for r in records[:limit_val]:
        compact_records.append({
            "speciesCode": r.get("speciesCode"),
            "comName": r.get("comName"),
            "sciName": r.get("sciName"),
            "locName": r.get("locName"),
            "obsDt": r.get("obsDt"),
            "howMany": r.get("howMany", 1),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "subId": r.get("subId"),
            "observer": r.get("observer")
        })

    if args.json:
        output_data = {
            "query_place": args.place or "dulan",
            "filter_user": filter_user,
            "center": {"lat": lat, "lng": lng, "dist_km": dist},
            "back_days": back_days,
            "total_observed_species": len(records),
            "showing_count": len(compact_records),
            "records": compact_records
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for cr in compact_records:
            print(f"{cr['speciesCode']}\t{cr['comName']}\t{cr['sciName']}\t{cr['obsDt']}\t{cr['subId']}")
    else:
        user_str = f" [限定觀察者: {filter_user}]" if filter_user else ""
        print(f"\n🦅 eBird 近期鳥況檢索 ({args.place or '都蘭'} 中心 {dist}km，回溯 {back_days} 天{user_str})")
        print(f"   總計目擊物種: {len(records)} 種，顯示前 {len(compact_records)} 筆:")
        print("-" * 85)
        for cr in compact_records:
            qty_str = f"{cr['howMany']} 隻" if cr['howMany'] else "有目擊"
            sub_str = f" [清單: {cr['subId']}]" if cr['subId'] else ""
            obs_str = f" | 👤 {cr['observer']}" if cr.get('observer') else ""
            print(f"[{cr['comName']}] ({cr['sciName']}) - {qty_str}{sub_str}{obs_str}")
            print(f"      📅 {cr['obsDt']} | 📍 {cr['locName']} ({cr['lat']:.4f}, {cr['lng']:.4f})")
        print("-" * 85 + "\n")

def cmd_historic(args, client: EbirdClient):
    """查詢歷史特定日期或區間之公共鳥況紀錄"""
    start_date_str = args.date
    end_date_str = args.end_date or start_date_str
    limit_val = getattr(args, "limit", 30)
    filter_user = getattr(args, "user", None)

    try:
        s_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        e_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD 格式 (例如: 2026-04-23)")

    if s_dt > e_dt:
        s_dt, e_dt = e_dt, s_dt

    _, place_info = load_place_config(args.place, args.place_config)
    c_lat, c_lng, dist_km = get_geo_params(place_info, args.lat, args.lng, args.radius)

    log_msg("INFO", f"正在檢索歷史鳥況 (區間: {start_date_str} ~ {end_date_str}, 區域: {args.place or '都蘭'})...", verbose=args.verbose)

    matched_records = []
    unique_species = {}
    curr_dt = s_dt

    # 台東縣 eBird 代碼固定為 TW-TTT
    region_code = "TW-TTT"

    while curr_dt <= e_dt:
        y, m, d = curr_dt.year, curr_dt.month, curr_dt.day
        endpoint = f"data/obs/{region_code}/historic/{y}/{m}/{d}"
        try:
            day_records = client.request(endpoint, {"sppLocale": "zh_TW"})
            for r in day_records:
                lat = r.get("lat")
                lng = r.get("lng")
                if lat is None or lng is None:
                    continue
                # 以 Haversine 演算法精確過濾距離
                dist = haversine_km(c_lat, c_lng, float(lat), float(lng))
                if dist <= dist_km:
                    r["dist_km"] = round(dist, 2)
                    matched_records.append(r)
                    com_name = r.get("comName")
                    if com_name not in unique_species:
                        unique_species[com_name] = r
        except Exception as e:
            log_msg("DEBUG", f"查詢歷史日期 {y}-{m}-{d} 失敗: {e}", verbose=args.verbose)
        curr_dt += timedelta(days=1)

    # 若指定 --user
    if filter_user:
        log_msg("INFO", f"正在過濾特定觀察者: '{filter_user}'...", verbose=args.verbose)
        user_filtered = []
        user_cache = {}
        for r in matched_records:
            sid = r.get("subId")
            if not sid:
                continue
            if sid not in user_cache:
                try:
                    chk = client.request(f"product/checklist/view/{sid}")
                    user_cache[sid] = chk.get("userDisplayName", "")
                except Exception:
                    user_cache[sid] = ""
            if filter_user.lower() in user_cache[sid].lower():
                r["observer"] = user_cache[sid]
                user_filtered.append(r)
        matched_records = user_filtered

    if args.json:
        output_data = {
            "query_place": args.place or "dulan",
            "date_range": f"{start_date_str} ~ {end_date_str}",
            "filter_user": filter_user,
            "total_records": len(matched_records),
            "unique_species": len(unique_species),
            "records": matched_records[:limit_val]
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for r in matched_records[:limit_val]:
            print(f"{r.get('obsDt')}\t{r.get('comName')}\t{r.get('locName')}\t{r.get('subId')}")
    else:
        user_str = f" [限定觀察者: {filter_user}]" if filter_user else ""
        print(f"\n📜 eBird 歷史鳥況查詢 ({args.place or '都蘭'} 半徑 {dist_km}km | {start_date_str} ~ {end_date_str}{user_str})")
        print(f"   總計目擊物種: {len(unique_species)} 種 (共 {len(matched_records)} 筆紀錄，顯示前 {min(len(matched_records), limit_val)} 筆):")
        print("-" * 85)
        for r in matched_records[:limit_val]:
            qty_str = f"{r.get('howMany')} 隻" if r.get('howMany') else "有目擊"
            sub_str = f" [清單: {r.get('subId')}]" if r.get('subId') else ""
            obs_str = f" | 👤 {r.get('observer')}" if r.get('observer') else ""
            print(f"[{r.get('comName')}] ({r.get('sciName')}) - {qty_str}{sub_str}{obs_str}")
            print(f"      📅 {r.get('obsDt')} | 📍 {r.get('locName')} (距中心 {r.get('dist_km')}km)")
        print("-" * 85 + "\n")

def cmd_hotspots(args, client: EbirdClient):
    """查詢周邊熱門賞鳥點"""
    limit_val = getattr(args, "limit", 15)
    back_days = getattr(args, "back", 14)
    _, place_info = load_place_config(args.place, args.place_config)
    lat, lng, dist = get_geo_params(place_info, args.lat, args.lng, args.radius)

    params = {
        "lat": lat,
        "lng": lng,
        "dist": int(dist),
        "back": back_days,
        "fmt": "json"
    }

    log_msg("INFO", f"正在檢索周邊賞鳥熱點 (中心: {lat:.4f},{lng:.4f}, 半徑: {dist}km)...", verbose=args.verbose)
    hotspots = client.request("ref/hotspot/geo", params)

    compact_hotspots = []
    for h in hotspots[:limit_val]:
        compact_hotspots.append({
            "locId": h.get("locId"),
            "locName": h.get("locName"),
            "latitude": h.get("lat"),
            "longitude": h.get("lng"),
            "numSpeciesAllTime": h.get("numSpeciesAllTime", 0)
        })

    if args.json:
        output_data = {
            "query_place": args.place or "dulan",
            "count": len(compact_hotspots),
            "hotspots": compact_hotspots
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for ch in compact_hotspots:
            print(f"{ch['locId']}\t{ch['locName']}\t{ch['latitude']},{ch['longitude']}")
    else:
        print(f"\n🔭 eBird 周邊熱門賞鳥點 ({args.place or '都蘭'} 半徑 {dist}km，共 {len(hotspots)} 個熱點):")
        print("-" * 75)
        for ch in compact_hotspots:
            species_info = f" (歷年累積: {ch['numSpeciesAllTime']} 種)" if ch['numSpeciesAllTime'] else ""
            print(f"📍 [{ch['locId']}] {ch['locName']}{species_info}")
            print(f"      座標: {ch['latitude']:.4f}, {ch['longitude']:.4f}")
        print("-" * 75 + "\n")

def cmd_notable(args, client: EbirdClient):
    """查詢近期罕見或稀有鳥種快訊"""
    back_days = getattr(args, "back", 14)
    _, place_info = load_place_config(args.place, args.place_config)
    lat, lng, dist = get_geo_params(place_info, args.lat, args.lng, args.radius)

    params = {
        "lat": lat,
        "lng": lng,
        "dist": int(dist),
        "back": min(max(back_days, 1), 30),
        "sppLocale": "zh_TW"
    }

    log_msg("INFO", f"正在檢索稀有鳥種快訊 (中心: {lat:.4f},{lng:.4f}, 回溯: {back_days}天)...", verbose=args.verbose)
    records = client.request("data/obs/geo/recent/notable", params)

    if args.json:
        print(json.dumps(records, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for r in records:
            print(f"{r.get('comName')}\t{r.get('locName')}\t{r.get('obsDt')}\t{r.get('subId')}")
    else:
        print(f"\n🚨 eBird 稀有與特異鳥況快訊 ({args.place or '都蘭'} 半徑 {dist}km，近 {back_days} 天):")
        print("-" * 75)
        if not records:
            print("   近期無特殊或罕見鳥種通報紀錄（均為穩定留鳥/常見鳥）。")
        else:
            for r in records:
                qty = f"{r.get('howMany')} 隻" if r.get('howMany') else "有目擊"
                sub_str = f" [清單: {r.get('subId')}]" if r.get('subId') else ""
                print(f"✨ [{r.get('comName')}] ({r.get('sciName')}) - {qty}{sub_str}")
                print(f"      📅 {r.get('obsDt')} | 📍 {r.get('locName')} ({r.get('lat'):.4f}, {r.get('lng'):.4f})")
        print("-" * 75 + "\n")

def cmd_match(args, client: EbirdClient):
    """比對關心鳥類名錄 (例如: 都蘭 12 種指標鳥)"""
    birds_data = load_birds_config(args.bird_file)
    species_list = birds_data.get("species", [])
    total_target = len(species_list)

    back_days = getattr(args, "back", 30)
    filter_user = getattr(args, "user", None)
    _, place_info = load_place_config(args.place, args.place_config)
    lat, lng, dist = get_geo_params(place_info, args.lat, args.lng, args.radius)

    params = {
        "lat": lat,
        "lng": lng,
        "dist": int(dist),
        "back": min(max(back_days, 1), 30),
        "sppLocale": "zh_TW"
    }

    log_msg("INFO", f"正在從 eBird 抓取近期觀測比對 {total_target} 種指標鳥類 (回溯: {back_days} 天)...", verbose=args.verbose)
    recent_obs = client.request("data/obs/geo/recent", params)

    if filter_user:
        user_cache = {}
        filtered_obs = []
        for obs in recent_obs:
            sid = obs.get("subId")
            if not sid:
                continue
            if sid not in user_cache:
                try:
                    chk = client.request(f"product/checklist/view/{sid}")
                    user_cache[sid] = chk.get("userDisplayName", "")
                except Exception:
                    user_cache[sid] = ""
            if filter_user.lower() in user_cache[sid].lower():
                obs["observer"] = user_cache[sid]
                filtered_obs.append(obs)
        recent_obs = filtered_obs

    obs_map_by_code = {}
    obs_map_by_sci = {}
    for obs in recent_obs:
        code = obs.get("speciesCode", "").lower()
        sci = obs.get("sciName", "").lower()
        if code and code not in obs_map_by_code:
            obs_map_by_code[code] = obs
        if sci and sci not in obs_map_by_sci:
            obs_map_by_sci[sci] = obs

    matched_results = []
    missing_results = []

    for sp in species_list:
        target_code = sp.get("ebird_code", "").lower()
        target_sci = sp.get("scientific_name", "").lower()

        hit = obs_map_by_code.get(target_code) or obs_map_by_sci.get(target_sci)

        if hit:
            matched_results.append({
                "id": sp.get("id"),
                "category": sp.get("category"),
                "common_name": sp.get("common_name"),
                "scientific_name": sp.get("scientific_name"),
                "ebird_code": sp.get("ebird_code"),
                "latest_date": hit.get("obsDt"),
                "latest_place": hit.get("locName"),
                "latest_lat": hit.get("lat"),
                "latest_lng": hit.get("lng"),
                "how_many": hit.get("howMany", 1),
                "subId": hit.get("subId"),
                "observer": hit.get("observer")
            })
        else:
            missing_results.append({
                "id": sp.get("id"),
                "category": sp.get("category"),
                "common_name": sp.get("common_name"),
                "scientific_name": sp.get("scientific_name"),
                "ebird_code": sp.get("ebird_code"),
                "notes": sp.get("notes")
            })

    coverage_rate = (len(matched_results) / total_target * 100) if total_target > 0 else 0.0

    output = {
        "title": birds_data.get("title", "鳥類名錄比對"),
        "place_filter": args.place or "dulan",
        "filter_user": filter_user,
        "back_days": back_days,
        "total_target_species": total_target,
        "matched_count": len(matched_results),
        "missing_count": len(missing_results),
        "coverage_rate_pct": round(coverage_rate, 2),
        "matched_birds": matched_results,
        "missing_birds": missing_results
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"COVERAGE\t{output['matched_count']}/{output['total_target_species']}\t{output['coverage_rate_pct']}%")
        for m in matched_results:
            print(f"MATCHED\t{m['common_name']}\t{m['scientific_name']}\t{m['latest_date']}\t{m['latest_lat']},{m['latest_lng']}")
    else:
        user_str = f" [限定觀察者: {filter_user}]" if filter_user else ""
        print(f"\n🕊️ {output['title']} - eBird 目擊比對")
        print(f"   地點: {output['place_filter']} (半徑 {dist}km) | 回溯: 近 {back_days} 天{user_str}")
        print(f"   🎯 近期目擊率: {output['matched_count']} / {output['total_target_species']} 種 ({output['coverage_rate_pct']}%)")
        print("\n✅ 近期有目擊紀錄 (命中清單):")
        print(f"{'類別':<12} {'鳥種名稱':<8} {'拉丁學名':<25} {'最新目擊時間與地點'}")
        print("-" * 85)
        for m in matched_results:
            coord_str = f"({m['latest_lat']:.4f},{m['latest_lng']:.4f})" if m['latest_lat'] else ""
            sub_str = f" [清單: {m['subId']}]" if m.get('subId') else ""
            obs_str = f" | 👤 {m['observer']}" if m.get('observer') else ""
            print(f"{m['category']:<12} {m['common_name']:<8} {m['scientific_name']:<25} {m['latest_date']} @ {m['latest_place']} {coord_str}{sub_str}{obs_str}")

        if missing_results:
            print(f"\n⭕ 近 {back_days} 天無回報鳥種 ({len(missing_results)} 種，可作為現地走讀尋鳥目標):")
            for miss in missing_results:
                print(f"   - [{miss['category']}] {miss['common_name']} ({miss['scientific_name']})")
        print()

def cmd_checklist(args, client: EbirdClient):
    """依 Submission ID (subId) 下鑽查詢該清單的觀察者與鳥種紀錄"""
    sub_id = args.sub_id
    log_msg("INFO", f"下鑽查詢 eBird 清單 #{sub_id}...", verbose=args.verbose)
    res = client.request(f"product/checklist/view/{sub_id}")

    obs_list = res.get("obs", [])
    loc = res.get("loc", {})
    user_display = res.get("userDisplayName") or "不公開"

    checklist_detail = {
        "subId": res.get("subId"),
        "projId": res.get("projId"),
        "user": user_display,
        "obsDt": res.get("obsDt"),
        "locName": loc.get("locName") or res.get("locId"),
        "latitude": loc.get("lat"),
        "longitude": loc.get("lng"),
        "durationMinutes": res.get("durationMinutes"),
        "numSpeciesReported": res.get("numSpeciesReported", len(obs_list)),
        "allObservationsReported": res.get("allObsReported", False),
        "species": []
    }

    for o in obs_list:
        checklist_detail["species"].append({
            "speciesCode": o.get("speciesCode"),
            "howMany": o.get("howManyStr") or o.get("howMany", 1),
            "comments": o.get("comments")
        })

    if args.json:
        print(json.dumps(checklist_detail, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"{checklist_detail['subId']}\t{checklist_detail['user']}\t{checklist_detail['obsDt']}\t{checklist_detail['numSpeciesReported']}")
    else:
        print(f"\n📋 eBird 觀察紀錄清單詳情 #{checklist_detail['subId']}")
        print(f"   ├─ 觀察者: {checklist_detail['user']}")
        print(f"   ├─ 專案來源: {checklist_detail['projId'] or 'eBird'}")
        print(f"   ├─ 時間: {checklist_detail['obsDt']}")
        print(f"   ├─ 地點: {checklist_detail['locName']} ({checklist_detail['latitude']}, {checklist_detail['longitude']})")
        print(f"   ├─ 記錄鳥種數: {checklist_detail['numSpeciesReported']} 種 (觀察歷時: {checklist_detail['durationMinutes'] or 'N/A'} 分鐘)")
        print("\n   目擊鳥種列表:")
        print("   " + "-" * 40)
        for sp in checklist_detail["species"]:
            comment_str = f" ({sp['comments']})" if sp['comments'] else ""
            print(f"   • {sp['speciesCode']:<15} 數量: {sp['howMany']}{comment_str}")
        print()

def cmd_user_csv(args, client: EbirdClient):
    """匯入個人歷史觀察 CSV (MyEBirdData.csv)，支援空間過濾、日期區間過濾與都蘭指標鳥自動對照"""
    csv_file = args.file
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"找不到指定的 CSV 檔案: {csv_file}")

    start_date = getattr(args, "start_date", None)
    end_date = getattr(args, "end_date", None)

    _, place_info = load_place_config(args.place, args.place_config)
    c_lat, c_lng, dist_km = get_geo_params(place_info, args.lat, args.lng, args.radius)

    log_msg("INFO", f"正在解析個人 eBird 歷史資料: {csv_file} (篩選區域: {args.place or '都蘭'})...", verbose=args.verbose)

    matched_records = []
    unique_species = {}

    with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                obs_date = row.get("Date") or row.get("obsDt") or ""
                # 日期篩選
                if start_date and obs_date < start_date:
                    continue
                if end_date and obs_date > end_date:
                    continue

                lat = float(row.get("Latitude") or row.get("lat") or 0)
                lng = float(row.get("Longitude") or row.get("lng") or 0)
                if lat == 0 or lng == 0:
                    continue

                d = haversine_km(c_lat, c_lng, lat, lng)
                if d <= dist_km:
                    com_name = row.get("Common Name") or row.get("comName") or "未知"
                    sci_name = row.get("Scientific Name") or row.get("sciName") or "Unknown"
                    loc_name = row.get("Location") or row.get("locName") or ""
                    sub_id = row.get("Submission ID") or row.get("subId") or ""

                    record = {
                        "common_name": com_name,
                        "scientific_name": sci_name,
                        "date": obs_date,
                        "location": loc_name,
                        "subId": sub_id,
                        "lat": lat,
                        "lng": lng,
                        "dist_km": round(d, 2)
                    }
                    matched_records.append(record)
                    if com_name not in unique_species:
                        unique_species[com_name] = record
            except Exception:
                continue

    # 指標鳥類名錄對照
    flora_stats = None
    if getattr(args, "bird_file", None) or getattr(args, "match_birds", False):
        birds_data = load_birds_config(getattr(args, "bird_file", None))
        total_target = len(birds_data.get("species", []))
        hit_target = 0
        hit_list = []
        for sp in birds_data.get("species", []):
            c_name = sp["common_name"]
            s_name = sp["scientific_name"].lower()
            hit = None
            for my_sp in unique_species.values():
                if my_sp["common_name"] == c_name or my_sp["scientific_name"].lower() == s_name:
                    hit = my_sp
                    break
            if hit:
                hit_target += 1
                hit_list.append(c_name)
        flora_stats = {
            "title": birds_data.get("title"),
            "target_count": total_target,
            "hit_count": hit_target,
            "hit_rate_pct": round(hit_target / total_target * 100, 2) if total_target > 0 else 0,
            "hit_species": hit_list
        }

    date_str = f" | 日期區間: {start_date or '不限'} ~ {end_date or '不限'}" if start_date or end_date else ""

    output_summary = {
        "file": os.path.basename(csv_file),
        "filter_place": args.place or "dulan",
        "date_filter": f"{start_date or 'all'} to {end_date or 'all'}",
        "filter_center": {"lat": c_lat, "lng": c_lng, "radius_km": dist_km},
        "total_records_in_area": len(matched_records),
        "unique_species_count": len(unique_species),
        "species_list": list(unique_species.values()),
        "target_birds_match": flora_stats
    }

    if args.json:
        print(json.dumps(output_summary, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for sp in output_summary["species_list"]:
            print(f"{sp['common_name']}\t{sp['scientific_name']}\t{sp['date']}\t{sp['location']}\t{sp['subId']}")
    else:
        print(f"\n📂 個人歷史觀察資料篩選結果 ({os.path.basename(csv_file)})")
        print(f"   篩選範圍: {output_summary['filter_place']} (半徑 {dist_km}km 內){date_str}")
        print(f"   🎯 都蘭累積鳥種: {len(unique_species)} 種 (總計目擊 {len(matched_records)} 次)")
        if flora_stats:
            print(f"   🕊️ 指標鳥名錄命中: {flora_stats['hit_count']} / {flora_stats['target_count']} 種 ({flora_stats['hit_rate_pct']}%) -> {', '.join(flora_stats['hit_species'])}")
        print("-" * 85)
        for sp in output_summary["species_list"]:
            print(f"• [{sp['common_name']}] ({sp['scientific_name']})")
            print(f"    📅 首筆/最新: {sp['date']} | 📍 {sp['location']} (距中心 {sp['dist_km']}km) [清單: {sp['subId']}]")
        print("-" * 85 + "\n")

def cmd_trip(args, client: EbirdClient):
    """匯入個人 CSV 分析指定日期區間內的旅行賞鳥足跡時間軸 (Trip Summary)"""
    csv_file = args.file
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"找不到指定的 CSV 檔案: {csv_file}")

    start_date = getattr(args, "start_date", None)
    end_date = getattr(args, "end_date", None)

    trip_records = []
    with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            obs_date = row.get("Date") or row.get("obsDt") or ""
            if start_date and obs_date < start_date:
                continue
            if end_date and obs_date > end_date:
                continue
            trip_records.append({
                "date": obs_date,
                "common_name": row.get("Common Name") or row.get("comName") or "未知",
                "scientific_name": row.get("Scientific Name") or row.get("sciName") or "Unknown",
                "location": row.get("Location") or row.get("locName") or "未知地點",
                "lat": float(row.get("Latitude") or row.get("lat") or 0),
                "lng": float(row.get("Longitude") or row.get("lng") or 0),
                "subId": row.get("Submission ID") or row.get("subId") or ""
            })

    trip_records.sort(key=lambda x: (x["date"], x["location"]))

    if args.json:
        print(json.dumps(trip_records, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for r in trip_records:
            print(f"{r['date']}\t{r['location']}\t{r['common_name']}\t{r['subId']}")
    else:
        print(f"\n🗺️ 賞鳥旅行足跡時間軸 (Trip Summary: {start_date or '起始'} ~ {end_date or '最新'})")
        print(f"   總計紀錄: {len(trip_records)} 筆目擊")
        print("-" * 85)
        current_date = None
        for r in trip_records:
            if r["date"] != current_date:
                current_date = r["date"]
                print(f"\n📅 【{current_date}】")
            coord_str = f"({r['lat']:.4f}, {r['lng']:.4f})" if r['lat'] and r['lng'] else ""
            print(f"   • {r['common_name']:<10} @ {r['location']} {coord_str} [清單: {r['subId']}]")
        print("\n" + "-" * 85 + "\n")

def cmd_export(args, client: EbirdClient):
    """匯出近期鳥況為 GeoJSON 或 CSV"""
    back_days = getattr(args, "back", 14)
    _, place_info = load_place_config(args.place, args.place_config)
    lat, lng, dist = get_geo_params(place_info, args.lat, args.lng, args.radius)

    params = {
        "lat": lat,
        "lng": lng,
        "dist": int(dist),
        "back": min(max(back_days, 1), 30),
        "sppLocale": "zh_TW"
    }

    log_msg("INFO", f"匯出近期鳥況資料 (格式: {args.format})...", verbose=args.verbose)
    records = client.request("data/obs/geo/recent", params)

    if args.format == "geojson":
        features = []
        for r in records:
            r_lat = r.get("lat")
            r_lng = r.get("lng")
            if not r_lat or not r_lng:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r_lng), float(r_lat)]
                },
                "properties": {
                    "speciesCode": r.get("speciesCode"),
                    "comName": r.get("comName"),
                    "sciName": r.get("sciName"),
                    "howMany": r.get("howMany", 1),
                    "locName": r.get("locName"),
                    "obsDt": r.get("obsDt"),
                    "subId": r.get("subId")
                }
            })
        export_obj = {
            "type": "FeatureCollection",
            "features": features
        }
        content = json.dumps(export_obj, ensure_ascii=False, indent=2)
    else:  # csv
        lines = ["speciesCode,comName,sciName,howMany,obsDt,locName,lng,lat,subId"]
        for r in records:
            c_name = (r.get("comName") or "").replace(",", " ")
            s_name = (r.get("sciName") or "").replace(",", " ")
            l_name = (r.get("locName") or "").replace(",", " ")
            lines.append(f"{r.get('speciesCode')},{c_name},{s_name},{r.get('howMany', 1)},{r.get('obsDt')},{l_name},{r.get('lng')},{r.get('lat')},{r.get('subId')}")
        content = "\n".join(lines)

    if args.output == "-":
        print(content)
    else:
        out_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        log_msg("INFO", f"已成功匯出至: {out_path}", verbose=args.verbose)
        if not args.quiet:
            print(f"✅ 檔案已成功匯出至: {out_path} (共 {len(records)} 筆紀錄)")

# ==================== CLI 主入口與參數解析 ====================

def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="啟用單行緊湊 JSON 輸出 (Token-Saving)")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="極簡輸出模式")
    parent_parser.add_argument("-v", "--verbose", action="store_true", help="輸出詳細除錯日誌 (至 stderr)")
    parent_parser.add_argument("-n", "--limit", type=int, default=20, help="限制回傳筆數 (預設: 20)")
    parent_parser.add_argument("-o", "--output", default="-", help="指定輸出檔案路徑 (預設: - 代表 stdout)")
    parent_parser.add_argument("--api-key", help="eBird API Key/Token (若未設定 EBIRD_API_KEY 環境變數時使用)")
    parent_parser.add_argument("--back", type=int, default=14, help="回溯查詢天數 (1~30 天，預設: 14 天)")
    parent_parser.add_argument("--user", help="限定特定觀察者姓名或代號 (例如: 'jason wu')")
    parent_parser.add_argument("--log-file", help="將 Log 同步寫入檔案 (傳入 AUTO 自動命名)")
    parent_parser.add_argument("--no-cache", action="store_true", help="停用本機 API 快取")
    parent_parser.add_argument("--manual", action="store_true", help="檢視完整說明書 (Rule 3)")

    parent_parser.add_argument("--place", default=None, help="指定區域代號 (預設讀取 places.json 之 dulan)")
    parent_parser.add_argument("--place-config", default=None, help="自訂區域設定檔路徑 (預設: data/ecology/places.json)")
    parent_parser.add_argument("--lat", type=float, help="以中心緯度覆蓋空間範圍")
    parent_parser.add_argument("--lng", type=float, help="以中心經度覆蓋空間範圍")
    parent_parser.add_argument("--radius", type=float, help="以半徑 (km) 覆蓋空間範圍")

    parser = argparse.ArgumentParser(
        description="eBird 在地鳥類生態觀測與即時鳥況 CLI (CGS v2.0 合規)",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="可用子命令")

    # 1. recent
    subparsers.add_parser("recent", parents=[parent_parser], help="查詢指定地點近期即時鳥況 (支援 --user)")

    # 2. historic
    p_hist = subparsers.add_parser("historic", parents=[parent_parser], help="查詢指定歷史日期或區間之公共鳥況")
    p_hist.add_argument("--date", required=True, help="起始歷史日期 (格式: YYYY-MM-DD)")
    p_hist.add_argument("--end-date", help="結束歷史日期 (格式: YYYY-MM-DD，預設與 --date 相同)")

    # 3. hotspots
    subparsers.add_parser("hotspots", parents=[parent_parser], help="探勘周邊經認證之熱門賞鳥點")

    # 4. notable
    subparsers.add_parser("notable", parents=[parent_parser], help="查詢近期罕見或稀有鳥種快訊")

    # 5. match
    p_match = subparsers.add_parser("match", parents=[parent_parser], help="比對關心鳥類名錄 (如都蘭 12 種指標鳥)")
    p_match.add_argument("--bird-file", default=None, help="自訂鳥類名錄 JSON (預設: data/ecology/dulan_birds.json)")

    # 6. checklist
    p_chk = subparsers.add_parser("checklist", parents=[parent_parser], help="依 Submission ID (subId) 下鑽查詢清單觀察者與詳細內容")
    p_chk.add_argument("sub_id", help="eBird 清單編號 (例如: S325666633)")

    # 7. user-csv
    p_csv = subparsers.add_parser("user-csv", parents=[parent_parser], help="匯入個人 CSV 進行空間、日期與指標鳥名錄篩選")
    p_csv.add_argument("file", help="個人 eBird CSV 檔案路徑")
    p_csv.add_argument("--start-date", help="起始日期 (YYYY-MM-DD)")
    p_csv.add_argument("--end-date", help="結束日期 (YYYY-MM-DD)")
    p_csv.add_argument("--bird-file", default=None, help="自訂指標鳥類名錄 JSON 進行交集命中率計算")
    p_csv.add_argument("--match-birds", action="store_true", help="自動對照預設指標鳥名錄 (dulan_birds.json)")

    # 8. trip
    p_trip = subparsers.add_parser("trip", parents=[parent_parser], help="匯入個人 CSV 產生指定行程之時間軸摘要 (Trip Summary)")
    p_trip.add_argument("file", help="個人 eBird CSV 檔案路徑")
    p_trip.add_argument("--start-date", help="旅行起始日期 (YYYY-MM-DD)")
    p_trip.add_argument("--end-date", help="旅行結束日期 (YYYY-MM-DD)")

    # 9. export
    p_exp = subparsers.add_parser("export", parents=[parent_parser], help="匯出空間圖資為 GeoJSON 或 CSV")
    p_exp.add_argument("--format", choices=["geojson", "csv"], default="geojson", help="匯出格式")

    # 10. schema
    subparsers.add_parser("schema", parents=[parent_parser], help="輸出自我描述 JSON Schema")

    # 11. manual
    subparsers.add_parser("manual", parents=[parent_parser], help="檢視說明手冊")

    # 位置引數向下相容 (Pillar 10)
    known_cmds = ["recent", "historic", "hotspots", "notable", "match", "checklist", "user-csv", "trip", "export", "schema", "manual", "-h", "--help"]
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "recent")

    args = parser.parse_args()

    if args.manual or args.subcommand == "manual":
        show_manual()
        sys.exit(0)

    if args.subcommand == "schema":
        print(json.dumps(get_schema(), ensure_ascii=False, indent=2))
        sys.exit(0)

    init_log_file(args.log_file)
    api_key = get_api_key(args.api_key)
    client = EbirdClient(api_key=api_key, use_cache=not args.no_cache, verbose=args.verbose)

    try:
        if args.subcommand in ("recent", "search"):
            cmd_recent(args, client)
        elif args.subcommand == "historic":
            cmd_historic(args, client)
        elif args.subcommand == "hotspots":
            cmd_hotspots(args, client)
        elif args.subcommand in ("notable", "rare"):
            cmd_notable(args, client)
        elif args.subcommand == "match":
            cmd_match(args, client)
        elif args.subcommand == "checklist":
            cmd_checklist(args, client)
        elif args.subcommand == "user-csv":
            cmd_user_csv(args, client)
        elif args.subcommand == "trip":
            cmd_trip(args, client)
        elif args.subcommand == "export":
            cmd_export(args, client)
        else:
            parser.print_help()
            sys.exit(0)
    except Exception as e:
        log_msg("ERROR", f"執行失敗: {e}", verbose=args.verbose)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
