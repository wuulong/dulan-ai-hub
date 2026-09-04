#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: inat_cli.py
title: iNaturalist 在地生態系與原民植物分析 CLI
description: 符合 CGS v2.1 規範的 iNaturalist 公民科學觀測資料查詢、二階段下鑽、都蘭原住民植物名錄對照整合比對、垂直海拔梯度與物候季節性分析工具。支援多物種批次檢索與同義學名自動容錯比對。
category: ecology
spec: @dulan-ai-hub/topics/inaturalist/inaturalist-dulan-flora-cli-spec.md
manual: @dulan-ai-hub/manuals/inat_cli.md
dependencies: urllib, json
cgs_version: 2.1
"""

import os
import sys
import json
import time
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# 顯式宣告 CGS 規格版號
__cli_spec_version__ = "2.1"

# 定錨至 dulan-ai-hub 專案根目錄
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_ROOT = PROJECT_ROOT
SPEC_PATH = os.path.join(PROJECT_ROOT, "topics/inaturalist/inaturalist-dulan-flora-cli-spec.md")
MANUAL_PATH = os.path.join(PROJECT_ROOT, "manuals/inat_cli.md")
DEFAULT_PLACES_PATH = os.path.join(PROJECT_ROOT, "data/ecology/places.json")
DEFAULT_FLORA_PATH = os.path.join(PROJECT_ROOT, "data/ecology/indigenous_flora.json")
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache/inat")

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
        log_file_path = os.path.join(log_dir, f"inat_cli_{timestamp}.log")
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
            "script": "inat_cli.py",
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
        "domain": "inat",
        "cgs_version": "2.0",
        "script": "scripts/gis/inat_cli.py",
        "description": "iNaturalist 在地生態系與原民植物分析 CLI，支援使用者觀察查詢、批次多物種檢索、原民植物對照整合、海拔與物候分析",
        "commands": {
            "user": {
                "description": "查詢 iNaturalist 使用者畫像、總觀察數、物種數與研究級比例",
                "args": ["username"]
            },
            "search": {
                "description": "多條件輕量搜尋觀測紀錄（支援 --taxon 單物種、--taxa 多物種逗號分隔、--flora-file 批次整份名錄查詢）",
                "args": ["--user", "--taxon", "--taxa", "--flora-file", "--place", "--place-config", "--quality", "-n/--limit"]
            },
            "fetch": {
                "description": "指定 Observation ID 取得單筆詳細資料（二階段下鑽之第二階段）",
                "args": ["observation_id"]
            },
            "match-flora": {
                "description": "將原住民族傳統植物名錄與指定使用者/地區之觀測紀錄對照整合比對（支援 synonyms 自動容錯與點位坐標輸出）",
                "args": ["--user", "--place", "--flora-file", "--quality"]
            },
            "analyze": {
                "description": "多維度生態分析（垂直海拔梯度 elevation 或物候季節性 phenology）",
                "args": ["--user", "--place", "--mode", "--flora-file"]
            },
            "export": {
                "description": "匯出觀測點資料為 GeoJSON 或 CSV 格式",
                "args": ["--user", "--place", "--format", "-o/--output"]
            },
            "schema": {
                "description": "輸出此 CLI 工具之自我描述 JSON Schema"
            }
        }
    }

class InatClient:
    """iNaturalist API v1 客戶端 (含快取與限速控制)"""
    BASE_URL = "https://api.inaturalist.org/v1"

    def __init__(self, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR, verbose: bool = False):
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.verbose = verbose
        if self.use_cache:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, endpoint: str, params: Dict[str, Any]) -> str:
        key_str = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
        hash_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, expire_hours: int = 24) -> Dict[str, Any]:
        params = params or {}
        params.setdefault("locale", "zh-TW")
        params.setdefault("preferred_place_id", 7140)

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
            headers={"User-Agent": "bmad-pa-inat-cli/2.0 (Taiwan locale; respectful-bot)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if cache_path:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                return data
        except urllib.error.HTTPError as e:
            err_msg = f"HTTP 錯誤 ({e.code}): {e.reason}"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e
        except Exception as e:
            err_msg = f"連線異常: {str(e)}"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e

def load_place_config(place_key: Optional[str] = None, place_config_path: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """載入空間區域定義檔"""
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

def load_flora_config(flora_path: Optional[str] = None) -> Dict[str, Any]:
    """載入原住民族植物名錄設定檔"""
    path = flora_path or DEFAULT_FLORA_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到植物名錄設定檔: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_spatial_params(place_info: Dict[str, Any], bbox_arg: Optional[str] = None,
                         lat_arg: Optional[float] = None, lng_arg: Optional[float] = None,
                         radius_arg: Optional[float] = None) -> Dict[str, Any]:
    """建立 iNaturalist 空間過濾參數"""
    params = {}
    if bbox_arg:
        parts = [float(x.strip()) for x in bbox_arg.split(",")]
        if len(parts) == 4:
            params["nelat"], params["nelng"], params["swlat"], params["swlng"] = parts
            return params

    if lat_arg is not None and lng_arg is not None:
        params["lat"] = lat_arg
        params["lng"] = lng_arg
        params["radius"] = radius_arg if radius_arg is not None else 10.0
        return params

    if "bbox" in place_info:
        bbox = place_info["bbox"]
        params["nelat"] = bbox.get("nelat")
        params["nelng"] = bbox.get("nelng")
        params["swlat"] = bbox.get("swlat")
        params["swlng"] = bbox.get("swlng")
    elif "center" in place_info:
        center = place_info["center"]
        params["lat"] = center.get("lat")
        params["lng"] = center.get("lng")
        params["radius"] = center.get("radius_km", 10.0)

    return params

# ==================== CLI 子命令核心邏輯 ====================

def cmd_user(args, client: InatClient):
    """查詢使用者畫像"""
    username = args.username
    log_msg("INFO", f"正在檢索觀察者畫像: {username}", verbose=args.verbose)
    res = client.request("users/autocomplete", {"q": username})
    results = res.get("results", [])
    matched = None
    for u in results:
        if u.get("login", "").lower() == username.lower():
            matched = u
            break
    if not matched and results:
        matched = results[0]

    if not matched:
        raise ValueError(f"找不到使用者: {username}")

    user_data = {
        "id": matched.get("id"),
        "login": matched.get("login"),
        "name": matched.get("name") or matched.get("login"),
        "observations_count": matched.get("observations_count", 0),
        "species_count": matched.get("species_count", 0),
        "identifications_count": matched.get("identifications_count", 0),
        "created_at": matched.get("created_at")
    }

    if args.json:
        print(json.dumps(user_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"{user_data['login']}\t{user_data['observations_count']}\t{user_data['species_count']}")
    else:
        print(f"\n👤 iNaturalist 觀察者: {user_data['name']} (@{user_data['login']})")
        print(f"   ├─ 總觀察紀錄數: {user_data['observations_count']:,} 筆")
        print(f"   ├─ 記錄物種數量: {user_data['species_count']:,} 種")
        print(f"   ├─ 參與社群鑑定: {user_data['identifications_count']:,} 次")
        print(f"   └─ 註冊日期: {user_data['created_at'][:10] if user_data['created_at'] else 'N/A'}\n")

def cmd_search(args, client: InatClient):
    """多條件搜尋觀測清單 (支援單物種、--taxa 多物種逗號分隔、--flora-file 名錄批次檢索)"""
    limit_val = getattr(args, "limit", 20)
    _, place_info = load_place_config(args.place, args.place_config)
    spatial_params = build_spatial_params(place_info, args.bbox, args.lat, args.lng, args.radius)

    target_queries = []
    # 模式 1: 傳入植物清單設定檔批次搜尋
    if getattr(args, "flora_file", None):
        flora_data = load_flora_config(args.flora_file)
        for sp in flora_data.get("species", []):
            target_queries.append({
                "query": sp["scientific_name"],
                "common_name": sp.get("common_name"),
                "indigenous_name": sp.get("indigenous_name"),
                "synonyms": sp.get("synonyms", [])
            })
    # 模式 2: 傳入多個物種逗號分隔 (--taxa "A,B,C")
    elif getattr(args, "taxa", None):
        for t in args.taxa.split(","):
            t_clean = t.strip()
            if t_clean:
                target_queries.append({"query": t_clean, "common_name": t_clean, "indigenous_name": "-", "synonyms": []})
    # 模式 3: 單一物種或無限定物種
    else:
        target_queries.append({
            "query": args.taxon,
            "common_name": args.taxon or "全部",
            "indigenous_name": "-",
            "synonyms": []
        })

    all_compact_records = []
    total_found_sum = 0

    log_msg("INFO", f"執行觀察紀錄檢索 (查詢物種數: {len(target_queries)}, 每種上限: {limit_val} 筆)...", verbose=args.verbose)

    for item in target_queries:
        query_taxon = item["query"]
        candidates = [query_taxon] if query_taxon else [None]
        if item["synonyms"]:
            candidates.extend(item["synonyms"])

        found_records_for_item = []
        for candidate in candidates:
            params = {"per_page": min(limit_val, 100), "order_by": "observed_on", "order": "desc"}
            if args.user:
                params["user_id"] = args.user
            if candidate:
                params["taxon_name"] = candidate
            if args.quality and args.quality != "any":
                params["quality_grade"] = args.quality
            params.update(spatial_params)

            try:
                res = client.request("observations", params)
                records = res.get("results", [])
                if records:
                    found_records_for_item = records
                    total_found_sum += res.get("total_results", 0)
                    break  # 命中則停止嘗試後續同義詞
            except Exception as e:
                log_msg("DEBUG", f"查詢 {candidate} 異常: {e}", verbose=args.verbose)

        for r in found_records_for_item:
            taxon = r.get("taxon") or {}
            coords = (r.get("geojson") or {}).get("coordinates", [None, None])
            all_compact_records.append({
                "id": r.get("id"),
                "observed_on": r.get("observed_on"),
                "common_name": taxon.get("preferred_common_name") or taxon.get("name") or "未知",
                "scientific_name": taxon.get("name") or "Unknown",
                "matched_query": item["common_name"],
                "indigenous_name": item["indigenous_name"],
                "user": (r.get("user") or {}).get("login"),
                "latitude": coords[1],
                "longitude": coords[0],
                "place_guess": r.get("place_guess") or "N/A",
                "quality_grade": r.get("quality_grade"),
                "photos_count": len(r.get("photos", [])),
                "photo_url": ((r.get("photos") or [{}])[0]).get("url")
            })

    if args.json:
        output_data = {
            "total_species_queried": len(target_queries),
            "count": len(all_compact_records),
            "records": all_compact_records
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for cr in all_compact_records:
            print(f"{cr['id']}\t{cr['common_name']}\t{cr['latitude']},{cr['longitude']}\t{cr['user']}\t{cr['observed_on']}")
    else:
        print(f"\n🔍 批次檢索結果 (共涵蓋 {len(target_queries)} 項物種，取得 {len(all_compact_records)} 筆紀錄):")
        print("-" * 80)
        for cr in all_compact_records:
            coord_str = f"({cr['latitude']:.5f}, {cr['longitude']:.5f})" if cr['latitude'] and cr['longitude'] else "無座標"
            print(f"[{cr['id']}] {cr['common_name']} ({cr['scientific_name']}) | 族語: {cr['indigenous_name']}")
            print(f"      📅 {cr['observed_on']} | 👤 @{cr['user']} | 📍 {cr['place_guess']} {coord_str}")
        print("-" * 80 + "\n")

def cmd_fetch(args, client: InatClient):
    """取得單筆詳細觀測紀錄"""
    obs_id = args.observation_id
    log_msg("INFO", f"下鑽取得觀察紀錄 #{obs_id} 詳細資料...", verbose=args.verbose)
    res = client.request(f"observations/{obs_id}")
    results = res.get("results", [])
    if not results:
        raise ValueError(f"找不到觀察紀錄 ID: {obs_id}")

    r = results[0]
    taxon = r.get("taxon") or {}
    photos = [p.get("url") for p in r.get("photos", []) if p.get("url")]

    detail = {
        "id": r.get("id"),
        "uri": r.get("uri"),
        "observed_on": r.get("observed_on"),
        "created_at": r.get("created_at"),
        "quality_grade": r.get("quality_grade"),
        "user": (r.get("user") or {}).get("login"),
        "taxon": {
            "id": taxon.get("id"),
            "name": taxon.get("name"),
            "preferred_common_name": taxon.get("preferred_common_name"),
            "rank": taxon.get("rank"),
            "wikipedia_url": taxon.get("wikipedia_url")
        },
        "location": {
            "latitude": (r.get("geojson") or {}).get("coordinates", [None, None])[1],
            "longitude": (r.get("geojson") or {}).get("coordinates", [None, None])[0],
            "place_guess": r.get("place_guess"),
            "positional_accuracy": r.get("positional_accuracy")
        },
        "description": r.get("description"),
        "photos": photos,
        "identifications_count": len(r.get("identifications", []))
    }

    if args.json:
        print(json.dumps(detail, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"{detail['id']}\t{detail['taxon']['name']}\t{detail['location']['latitude']},{detail['location']['longitude']}")
    else:
        print(f"\n📖 觀察紀錄詳情 #{detail['id']}")
        print(f"   ├─ 物種: {detail['taxon']['preferred_common_name']} ({detail['taxon']['name']})")
        print(f"   ├─ 觀察者: @{detail['user']}")
        print(f"   ├─ 時間: {detail['observed_on']} (建立於 {detail['created_at'][:10]})")
        print(f"   ├─ 地點: {detail['location']['place_guess']}")
        print(f"   │  └─ 座標: {detail['location']['latitude']}, {detail['location']['longitude']}")
        print(f"   ├─ 品質等級: {detail['quality_grade']} (社群鑑定: {detail['identifications_count']} 次)")
        print(f"   ├─ 照片數量: {len(detail['photos'])} 張")
        if detail['photos']:
            print(f"   │  └─ 第一張: {detail['photos'][0]}")
        print(f"   └─ 連結: {detail['uri']}\n")

def cmd_match_flora(args, client: InatClient):
    """原住民生活植物名錄對照整合比對 (支援 synonyms 同義學名容錯與實體座標輸出)"""
    flora_data = load_flora_config(args.flora_file)
    species_list = flora_data.get("species", [])
    total_target = len(species_list)

    _, place_info = load_place_config(args.place, args.place_config)
    spatial_params = build_spatial_params(place_info, args.bbox, args.lat, args.lng, args.radius)

    log_msg("INFO", f"開始進行原住民植物名錄對照整合 (共 {total_target} 種植物，支援同義學名自動容錯)...", verbose=args.verbose)

    matched_results = []
    missing_results = []

    for sp in species_list:
        primary_sci_name = sp["scientific_name"]
        candidates = [primary_sci_name] + sp.get("synonyms", [])

        hit_records = []
        matched_candidate = None
        total_obs = 0

        for cand in candidates:
            params = {"taxon_name": cand, "per_page": 5, "order_by": "observed_on", "order": "desc"}
            if args.user:
                params["user_id"] = args.user
            if args.quality and args.quality != "any":
                params["quality_grade"] = args.quality
            params.update(spatial_params)

            try:
                res = client.request("observations", params)
                obs_count = res.get("total_results", 0)
                if obs_count > 0:
                    total_obs = obs_count
                    hit_records = res.get("results", [])
                    matched_candidate = cand
                    break
            except Exception as e:
                log_msg("DEBUG", f"比對 {cand} 異常: {e}", verbose=args.verbose)

        if total_obs > 0 and hit_records:
            first_rec = hit_records[-1]
            latest_rec = hit_records[0]
            latest_coords = (latest_rec.get("geojson") or {}).get("coordinates", [None, None])
            matched_results.append({
                "id": sp.get("id"),
                "category": sp.get("category"),
                "common_name": sp.get("common_name"),
                "indigenous_name": sp.get("indigenous_name"),
                "scientific_name": primary_sci_name,
                "matched_scientific_name": matched_candidate,
                "total_observations": total_obs,
                "latest_date": latest_rec.get("observed_on"),
                "first_date": first_rec.get("observed_on"),
                "latest_user": (latest_rec.get("user") or {}).get("login"),
                "latest_lat": latest_coords[1],
                "latest_lng": latest_coords[0],
                "latest_place": latest_rec.get("place_guess"),
                "sample_obs_id": latest_rec.get("id")
            })
        else:
            missing_results.append({
                "id": sp.get("id"),
                "category": sp.get("category"),
                "common_name": sp.get("common_name"),
                "indigenous_name": sp.get("indigenous_name"),
                "scientific_name": primary_sci_name,
                "notes": sp.get("notes")
            })

    coverage_rate = (len(matched_results) / total_target * 100) if total_target > 0 else 0.0

    output = {
        "title": flora_data.get("title", "原住民植物名錄比對"),
        "target_user": args.user or "全部觀察者",
        "place_filter": args.place or "預設地區",
        "total_target_species": total_target,
        "matched_count": len(matched_results),
        "missing_count": len(missing_results),
        "coverage_rate_pct": round(coverage_rate, 2),
        "matched_species": matched_results,
        "missing_species": missing_results
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"COVERAGE\t{output['matched_count']}/{output['total_target_species']}\t{output['coverage_rate_pct']}%")
        for m in matched_results:
            print(f"MATCHED\t{m['scientific_name']}\t{m['common_name']}\t{m['total_observations']}\t{m['latest_lat']},{m['latest_lng']}")
    else:
        print(f"\n🌾 {output['title']} - 對照整合成果")
        print(f"   觀察者: {output['target_user']} | 地區: {output['place_filter']}")
        print(f"   🎯 名錄命中率: {output['matched_count']} / {output['total_target_species']} 種 ({output['coverage_rate_pct']}%)")
        print("\n✅ 已記錄物種 (命中清單與代表點座標):")
        print(f"{'類別':<10} {'俗名':<8} {'族語名':<15} {'學名':<25} {'次數':<5} {'最新座標與地點'}")
        print("-" * 88)
        for m in matched_results:
            coord_str = f"({m['latest_lat']:.4f},{m['latest_lng']:.4f})" if m['latest_lat'] and m['latest_lng'] else "N/A"
            user_str = f"@{m['latest_user']}" if m['latest_user'] else ""
            print(f"{m['category']:<10} {m['common_name']:<8} {m['indigenous_name']:<15} {m['scientific_name']:<25} {m['total_observations']:<5} {coord_str} {user_str}")

        if missing_results:
            print(f"\n⭕ 尚未記錄物種 ({len(missing_results)} 種，未來田野空缺):")
            for miss in missing_results:
                print(f"   - [{miss['category']}] {miss['common_name']} ({miss['indigenous_name']}) -> {miss['scientific_name']}")
        print()

def cmd_analyze(args, client: InatClient):
    """多維度生態分析 (海拔垂直梯度 elevation / 物候季節性 phenology)"""
    flora_data = load_flora_config(args.flora_file)
    species_list = flora_data.get("species", [])
    target_sci_names = set()
    for sp in species_list:
        target_sci_names.add(sp["scientific_name"])
        for syn in sp.get("synonyms", []):
            target_sci_names.add(syn)

    _, place_info = load_place_config(args.place, args.place_config)
    spatial_params = build_spatial_params(place_info, args.bbox, args.lat, args.lng, args.radius)

    log_msg("INFO", f"抓取觀察數據進行多維度分析 (模式: {args.mode})...", verbose=args.verbose)
    fetch_params = {"per_page": 200, "order_by": "observed_on", "order": "desc"}
    if args.user:
        fetch_params["user_id"] = args.user
    fetch_params.update(spatial_params)

    res = client.request("observations", fetch_params)
    records = res.get("results", [])

    # 1. 物候季節性分析 (月份分佈)
    month_counts = {m: 0 for m in range(1, 13)}
    flora_month_counts = {m: 0 for m in range(1, 13)}
    elevation_bins = {"海岸帶 (<50m)": 0, "平原聚落 (50-200m)": 0, "淺山坡地 (200-500m)": 0, "中高山林 (>500m)": 0, "未記載高程": 0}

    for r in records:
        dt_str = r.get("observed_on")
        taxon_name = (r.get("taxon") or {}).get("name", "")
        if dt_str and len(dt_str) >= 7:
            try:
                m = int(dt_str[5:7])
                month_counts[m] += 1
                if taxon_name in target_sci_names:
                    flora_month_counts[m] += 1
            except Exception:
                pass

        coords = (r.get("geojson") or {}).get("coordinates")
        if coords:
            lng, lat = coords[0], coords[1]
            if lng >= 121.225:
                elevation_bins["海岸帶 (<50m)"] += 1
            elif lng >= 121.205:
                elevation_bins["平原聚落 (50-200m)"] += 1
            elif lng >= 121.190:
                elevation_bins["淺山坡地 (200-500m)"] += 1
            else:
                elevation_bins["中高山林 (>500m)"] += 1
        else:
            elevation_bins["未記載高程"] += 1

    analysis_result = {
        "user": args.user or "all",
        "sample_size": len(records),
        "elevation_gradient": elevation_bins,
        "monthly_phenology": {
            "all_observations": month_counts,
            "indigenous_flora_only": flora_month_counts
        }
    }

    if args.json:
        print(json.dumps(analysis_result, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print("MONTH\tALL\tFLORA")
        for m in range(1, 13):
            print(f"{m}月\t{month_counts[m]}\t{flora_month_counts[m]}")
    else:
        print(f"\n📊 生態系多維度分析報告 (樣本數: {len(records)} 筆)")
        if args.mode in ("elevation", "both"):
            print("\n🏔️ 垂直海拔梯度空間分佈 (估計值):")
            for k, v in elevation_bins.items():
                bar = "█" * (v // 3)
                pct = (v / len(records) * 100) if records else 0
                print(f"   {k:<16} : {v:>3} 筆 ({pct:4.1f}%) {bar}")

        if args.mode in ("phenology", "both"):
            print("\n🌸 物候季節性 (1~12 月份觀察分佈熱力):")
            print(f"   {'月份':<6} {'全部觀察':<10} {'原民植物觀察'}")
            print("   " + "-" * 35)
            for m in range(1, 13):
                all_bar = "▓" * (month_counts[m] // 4)
                flora_bar = "█" * (flora_month_counts[m])
                print(f"   {m:>2} 月 : {month_counts[m]:>3} 筆 {all_bar:<10} | 原民植物: {flora_month_counts[m]:>2} 筆 {flora_bar}")
            print("\n   💡 文化備註: 刺桐 (tayuk) 在 2~4 月紅花期為阿美族傳統開春與飛魚季指標。\n")

def cmd_export(args, client: InatClient):
    """匯出空間圖資 (GeoJSON / CSV)"""
    limit_val = getattr(args, "limit", 200)
    params = {"per_page": min(limit_val, 200), "order_by": "observed_on", "order": "desc"}
    if args.user:
        params["user_id"] = args.user

    _, place_info = load_place_config(args.place, args.place_config)
    spatial_params = build_spatial_params(place_info, args.bbox, args.lat, args.lng, args.radius)
    params.update(spatial_params)

    log_msg("INFO", f"匯出觀察資料 (格式: {args.format})...", verbose=args.verbose)
    res = client.request("observations", params)
    records = res.get("results", [])

    if args.format == "geojson":
        features = []
        for r in records:
            coords = (r.get("geojson") or {}).get("coordinates")
            if not coords:
                continue
            taxon = r.get("taxon") or {}
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coords
                },
                "properties": {
                    "id": r.get("id"),
                    "observed_on": r.get("observed_on"),
                    "common_name": taxon.get("preferred_common_name"),
                    "scientific_name": taxon.get("name"),
                    "user": (r.get("user") or {}).get("login"),
                    "quality_grade": r.get("quality_grade"),
                    "uri": r.get("uri")
                }
            })
        export_obj = {
            "type": "FeatureCollection",
            "features": features
        }
        content = json.dumps(export_obj, ensure_ascii=False, indent=2)
    else:  # csv
        lines = ["id,observed_on,common_name,scientific_name,user,quality_grade,lng,lat"]
        for r in records:
            coords = (r.get("geojson") or {}).get("coordinates", ["", ""])
            taxon = r.get("taxon") or {}
            c_name = (taxon.get("preferred_common_name") or "").replace(",", " ")
            s_name = (taxon.get("name") or "").replace(",", " ")
            u_name = (r.get("user") or {}).get("login", "")
            q_grade = r.get("quality_grade", "")
            lines.append(f"{r.get('id')},{r.get('observed_on')},{c_name},{s_name},{u_name},{q_grade},{coords[0]},{coords[1]}")
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

def cmd_bird_sounds(args, client: InatClient):
    """查詢並下載都蘭 12 種指標鳥類的野外高品質鳴唱音訊"""
    birds_file = args.birds_file or os.path.join(PROJECT_ROOT, "data/ecology/dulan_birds.json")
    if not os.path.exists(birds_file):
        raise FileNotFoundError(f"找不到指標鳥類設定檔: {birds_file}")

    with open(birds_file, "r", encoding="utf-8") as f:
        birds_data = json.load(f)
    birds = birds_data.get("species") or birds_data.get("birds") or []

    out_dir = os.path.abspath(args.sound_dir or os.path.join(PROJECT_ROOT, "data/ecology/sounds"))
    if args.download:
        os.makedirs(out_dir, exist_ok=True)

    log_msg("INFO", f"開始檢索 {len(birds)} 種都蘭指標鳥類的野外錄音資產 (下載模式: {args.download})...", verbose=args.verbose)

    sound_results = []
    for b in birds:
        b_id = b.get("id")
        c_name = b.get("common_name")
        sci = b.get("scientific_name")

        params = {
            "taxon_name": sci,
            "sounds": "true",
            "per_page": 5,
            "order_by": "observed_on",
            "order": "desc"
        }

        rec_item = None
        total_rec = 0
        try:
            res = client.request("observations", params)
            total_rec = res.get("total_results", 0)
            results = res.get("results", [])

            if results:
                for cand_obs in results:
                    sounds = cand_obs.get("sounds", [])
                    if sounds and sounds[0].get("file_url"):
                        rec_item = {
                            "obs_id": cand_obs.get("id"),
                            "observed_on": cand_obs.get("observed_on"),
                            "user": (cand_obs.get("user") or {}).get("login"),
                            "place_guess": cand_obs.get("place_guess"),
                            "sound_id": sounds[0].get("id"),
                            "file_url": sounds[0].get("file_url"),
                            "file_type": sounds[0].get("file_content_type"),
                            "license": sounds[0].get("license_code"),
                            "attribution": sounds[0].get("attribution")
                        }
                        break
        except Exception as e:
            log_msg("WARN", f"檢索 {c_name} 錄音失敗: {e}", verbose=args.verbose)

        download_path = None
        if rec_item and args.download:
            ext = ".m4a" if "mp4" in rec_item["file_type"] else ".mp3"
            filename = f"{b_id}_{c_name}_{rec_item['sound_id']}{ext}"
            file_dest = os.path.join(out_dir, filename)

            if not os.path.exists(file_dest):
                log_msg("INFO", f"正在下載 {c_name} 鳴唱音檔 ➔ {filename}...", verbose=args.verbose)
                try:
                    req = urllib.request.Request(
                        rec_item["file_url"],
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": "https://www.inaturalist.org/"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp, open(file_dest, "wb") as f_out:
                        f_out.write(resp.read())
                    download_path = file_dest
                except Exception as dl_err:
                    log_msg("ERROR", f"下載 {c_name} 失敗: {dl_err}", verbose=args.verbose)
            else:
                download_path = file_dest

        sound_results.append({
            "id": b_id,
            "category": b.get("category"),
            "common_name": c_name,
            "scientific_name": sci,
            "total_recordings_available": total_rec,
            "recording": rec_item,
            "local_file": download_path
        })
        time.sleep(0.3)

    if args.json:
        output_data = {
            "total_birds": len(birds),
            "sounds_dir": out_dir if args.download else None,
            "results": sound_results
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for sr in sound_results:
            rec = sr.get("recording") or {}
            print(f"{sr['id']}\t{sr['common_name']}\t{sr['total_recordings_available']}\t{sr.get('local_file') or rec.get('file_url')}")
    else:
        print(f"\n🎵 都蘭 12 種指標鳥類野外鳴唱音訊清單 (iNaturalist 官方庫存)")
        if args.download:
            print(f"   💾 離線音檔儲存目錄: {out_dir}")
        print("-" * 90)
        print(f"{'編號':<8} {'中文名稱':<8} {'學名':<24} {'庫存筆數':<8} {'狀態 / 本地檔案 / 錄音資訊'}")
        print("-" * 90)
        for sr in sound_results:
            rec = sr.get("recording")
            if rec:
                stat_str = f"✅ 已下載: {os.path.basename(sr['local_file'])}" if sr.get("local_file") else f"🔗 直連音檔 (Obs #{rec['obs_id']})"
                lic_str = f"[{rec['license'] or 'All rights'}]"
                print(f"[{sr['id']:<6}] {sr['common_name']:<8} {sr['scientific_name']:<24} {sr['total_recordings_available']:>4} 筆     {stat_str} {lic_str}")
            else:
                print(f"[{sr['id']:<6}] {sr['common_name']:<8} {sr['scientific_name']:<24} 暫無錄音")
        print("-" * 90 + "\n")

# ==================== CLI 主入口與參數解析 ====================

def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="啟用單行緊湊 JSON 輸出 (Token-Saving)")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="極簡輸出模式")
    parent_parser.add_argument("-v", "--verbose", action="store_true", help="輸出詳細除錯日誌 (至 stderr)")
    parent_parser.add_argument("-n", "--limit", type=int, default=20, help="限制回傳筆數 (預設: 20)")
    parent_parser.add_argument("-o", "--output", default="-", help="指定輸出檔案路徑 (預設: - 代表 stdout)")
    parent_parser.add_argument("--log-file", help="將 Log 同步寫入檔案 (傳入 AUTO 自動命名)")
    parent_parser.add_argument("--no-cache", action="store_true", help="停用本機 API 快取")
    parent_parser.add_argument("--manual", action="store_true", help="檢視完整說明書 (Rule 3)")

    parent_parser.add_argument("--place", default=None, help="指定區域代號 (預設為 places.json 定義之 dulan，傳入 any 代表不限)")
    parent_parser.add_argument("--place-config", default=None, help="自訂區域設定檔路徑 (預設: data/ecology/places.json)")
    parent_parser.add_argument("--bbox", help="以四角座標覆蓋空間範圍: nelat,nelng,swlat,swlng")
    parent_parser.add_argument("--lat", type=float, help="以中心緯度覆蓋空間範圍")
    parent_parser.add_argument("--lng", type=float, help="以中心經度覆蓋空間範圍")
    parent_parser.add_argument("--radius", type=float, help="以半徑 (km) 覆蓋空間範圍")

    parser = argparse.ArgumentParser(
        description="iNaturalist 在地生態系與原民植物分析 CLI (CGS v2.0 合規)",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="可用子命令")

    # 1. user
    p_user = subparsers.add_parser("user", parents=[parent_parser], help="查詢觀察者畫像")
    p_user.add_argument("username", help="iNaturalist 使用者帳號")

    # 2. search (升級支援 --taxa 與 --flora-file 批次檢索)
    p_search = subparsers.add_parser("search", parents=[parent_parser], help="輕量檢索觀測紀錄 (支援多物種/名錄批次查)")
    p_search.add_argument("--user", help="限定特定觀察者")
    p_search.add_argument("--taxon", help="限定單一物種學名或俗名")
    p_search.add_argument("--taxa", help="以逗號分隔批次查詢多個物種 (例如: 'Pandanus,Zanthoxylum,Erythrina')")
    p_search.add_argument("--flora-file", default=None, help="指定原住民植物名錄 JSON 進行整份批次比對檢索")
    p_search.add_argument("--quality", choices=["research", "needs_id", "casual", "any"], default="any", help="資料品質等級")

    # 3. fetch
    p_fetch = subparsers.add_parser("fetch", parents=[parent_parser], help="取得單筆觀測詳情")
    p_fetch.add_argument("observation_id", help="Observation ID")

    # 4. match-flora
    p_match = subparsers.add_parser("match-flora", parents=[parent_parser], help="原住民族植物名錄對照整合比對")
    p_match.add_argument("--user", help="限定特定觀察者 (例如: jimchen1)")
    p_match.add_argument("--flora-file", default=None, help="自訂植物名錄 JSON (預設: data/ecology/indigenous_flora.json)")
    p_match.add_argument("--quality", choices=["research", "needs_id", "casual", "any"], default="any", help="資料品質等級")

    # 5. analyze
    p_ana = subparsers.add_parser("analyze", parents=[parent_parser], help="多維度生態分析")
    p_ana.add_argument("--user", help="限定特定觀察者")
    p_ana.add_argument("--mode", choices=["elevation", "phenology", "both"], default="both", help="分析維度")
    p_ana.add_argument("--flora-file", default=None, help="自訂植物名錄 JSON")

    # 6. export
    p_exp = subparsers.add_parser("export", parents=[parent_parser], help="匯出空間圖資")
    p_exp.add_argument("--user", help="限定特定觀察者")
    p_exp.add_argument("--format", choices=["geojson", "csv"], default="geojson", help="匯出格式")

    # 7. bird-sounds
    p_sounds = subparsers.add_parser("bird-sounds", parents=[parent_parser], help="檢索與下載都蘭 12 種指標鳥類的野外錄音")
    p_sounds.add_argument("--birds-file", default=None, help="自訂鳥類名錄 JSON (預設: data/ecology/dulan_birds.json)")
    p_sounds.add_argument("--download", action="store_true", help="將高品質音檔下載至本機目錄")
    p_sounds.add_argument("--sound-dir", default=None, help="指定音檔下載目錄 (預設: data/ecology/sounds)")

    # 8. schema
    subparsers.add_parser("schema", parents=[parent_parser], help="輸出自我描述 JSON Schema")

    # 9. manual
    subparsers.add_parser("manual", parents=[parent_parser], help="檢視說明手冊")

    # 位置引數降級向下相容 (Pillar 10)
    known_cmds = ["user", "search", "fetch", "match-flora", "analyze", "export", "bird-sounds", "schema", "manual", "-h", "--help"]
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "search")

    args = parser.parse_args()

    if args.manual or args.subcommand == "manual":
        show_manual()
        sys.exit(0)

    if args.subcommand == "schema":
        print(json.dumps(get_schema(), ensure_ascii=False, indent=2))
        sys.exit(0)

    init_log_file(args.log_file)
    client = InatClient(use_cache=not args.no_cache, verbose=args.verbose)

    try:
        if args.subcommand == "user":
            cmd_user(args, client)
        elif args.subcommand == "search":
            cmd_search(args, client)
        elif args.subcommand == "fetch":
            cmd_fetch(args, client)
        elif args.subcommand == "match-flora":
            cmd_match_flora(args, client)
        elif args.subcommand == "analyze":
            cmd_analyze(args, client)
        elif args.subcommand == "export":
            cmd_export(args, client)
        elif args.subcommand in ("bird-sounds", "sounds"):
            cmd_bird_sounds(args, client)
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
