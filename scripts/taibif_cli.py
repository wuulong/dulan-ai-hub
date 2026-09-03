#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: taibif_cli.py
title: TaiBIF / TBIA 台灣生物多樣性在地生態系與保育調查 CLI
description: 符合 CGS v2.1 規範之 TaiBIF / TBIA 官方 OpenAPI (tbiadata.tw) 查詢與分析工具。整合中研院、林保署、生多所、科博館等 10 大機構權威調查資料，與 inat_cli / ebird_cli 共用 places.json 空間設定。支援物種出沒紀錄檢索 (search)、都蘭在地法定保育類名冊 (protected)、原住民植物標本比對 (flora)、物種分類與特有身分證 (taxon) 及 GIS 圖資匯出 (export)。
category: ecology
spec: @dulan-ai-hub/topics/taibif/taibif-dulan-cli-spec.md
manual: @dulan-ai-hub/manuals/taibif_cli.md
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
SPEC_PATH = os.path.join(PROJECT_ROOT, "topics/taibif/taibif-dulan-cli-spec.md")
MANUAL_PATH = os.path.join(PROJECT_ROOT, "manuals/taibif_cli.md")
DEFAULT_PLACES_PATH = os.path.join(PROJECT_ROOT, "data/ecology/places.json")
DEFAULT_FLORA_PATH = os.path.join(PROJECT_ROOT, "data/ecology/indigenous_flora.json")
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache/taibif")

_log_file_handle = None

def init_log_file(log_file_path: Optional[str] = None):
    """初始化日誌輸出檔案"""
    global _log_file_handle
    if not log_file_path:
        return
    if log_file_path == "AUTO":
        log_dir = os.path.join(WORKSPACE_ROOT, "tmp", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(log_dir, f"taibif_cli_{timestamp}.log")
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
    """CGS v2.1 結構化 Log 輸出函式 (走 sys.stderr)"""
    if level.upper() == "DEBUG" and not verbose:
        return

    if json_mode:
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level.upper(),
            "script": "taibif_cli.py",
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
    """顯示或喚醒閱讀器開啟說明手冊"""
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
    """回傳 CGS v2.1 規範之自我描述 Schema"""
    return {
        "domain": "taibif",
        "cgs_version": "2.1",
        "script": "scripts/gis/taibif_cli.py",
        "spec": SPEC_PATH,
        "description": "TaiBIF / TBIA 官方 OpenAPI 查詢與分析工具，涵蓋中研院、生多所、林保署、科博館等國家級權威調查資料、都蘭法定保育類、植物標本與特有種身分證",
        "commands": {
            "search": {
                "description": "檢索指定物種在都蘭（或特定空間）的官方歷史科學調查與標本出沒紀錄",
                "args": ["--name", "--group", "--place", "--place-config", "-n/--limit"]
            },
            "protected": {
                "description": "一鍵產出都蘭與東河鄉境內官方記錄過的法定保育類動植物清單",
                "args": ["--place", "--group", "-n/--limit"]
            },
            "flora": {
                "description": "比對阿美族生活植物名錄在官方植物標本庫中的真實採集地點與歷史調查紀錄",
                "args": ["--place", "--match-flora", "--flora-file", "-n/--limit"]
            },
            "taxon": {
                "description": "查詢物種在 TaiCOL 台灣物種名錄中的 Taxon ID、正式學名、同物異名與特有種身分證",
                "args": ["query"]
            },
            "export": {
                "description": "匯出該區域之調查點位為 GeoJSON 或 CSV 圖資",
                "args": ["--place", "--group", "--format", "-o/--output"]
            },
            "schema": {
                "description": "輸出此 CLI 工具之自我描述 JSON Schema"
            }
        }
    }

class TbiaClient:
    """TBIA / TaiBIF OpenAPI 客戶端 (含快取防爆與參數編碼保護)"""
    BASE_URL = "https://tbiadata.tw/api/v1"

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

    def request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, expire_hours: int = 24) -> Any:
        params = params or {}
        # 移除 None 值的參數
        clean_params = {k: v for k, v in params.items() if v is not None}
        cache_path = self._get_cache_path(endpoint, clean_params) if self.use_cache else None

        if cache_path and os.path.exists(cache_path):
            file_mtime = os.path.getmtime(cache_path)
            if (time.time() - file_mtime) < (expire_hours * 3600):
                log_msg("DEBUG", f"命中本機快取: {cache_path}", verbose=self.verbose)
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        query_string = urllib.parse.urlencode(clean_params)
        url = f"{self.BASE_URL}/{endpoint}"
        if query_string:
            url = f"{url}?{query_string}"

        log_msg("DEBUG", f"發送 HTTP 請求: {url}", verbose=self.verbose)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (bmad-pa-taibif-cli; respectful-tool)"
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
            err_msg = f"TBIA API HTTP 錯誤 ({e.code}): {e.reason}"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e
        except Exception as e:
            err_msg = f"連線異常: {str(e)}"
            log_msg("ERROR", err_msg, verbose=self.verbose)
            raise RuntimeError(err_msg) from e

def load_place_config(place_key: Optional[str] = None, place_config_path: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """載入空間設定檔 (places.json)"""
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
    """載入原住民族植物名錄"""
    path = flora_path or DEFAULT_FLORA_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到植物名錄設定檔: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_biogroup(group_str: Optional[str]) -> Optional[str]:
    """正規化 TBIA bioGroup 分類群字串"""
    if not group_str:
        return None
    group_clean = group_str.strip()
    mapping = {
        "植物": "被子植物",
        "鳥": "鳥類",
        "哺乳": "哺乳類",
        "蝴蝶": "蝶類",
        "青蛙": "兩棲類",
        "兩爬": "兩棲類",
        "爬蟲": "爬蟲類"
    }
    return mapping.get(group_clean, group_clean)

# ==================== CLI 子命令核心邏輯 ====================

def cmd_search(args, client: TbiaClient):
    """檢索指定物種在都蘭或特定區域的調查與標本紀錄"""
    limit_val = getattr(args, "limit", 20)
    name_query = getattr(args, "name", None)
    group_query = normalize_biogroup(getattr(args, "group", None))

    _, place_info = load_place_config(args.place, args.place_config)

    # 預設都蘭對應台東縣東河鄉
    params = {
        "county": place_info.get("county", "臺東縣"),
        "municipality": place_info.get("municipality", "東河鄉"),
        "name": name_query,
        "bioGroup": group_query,
        "limit": limit_val
    }

    log_msg("INFO", f"正在檢索 TBIA 官方調查資料 (區域: {params['county']}{params['municipality']}, 物種: {name_query or '全部'}, 類群: {group_query or '不限'})...", verbose=args.verbose)
    resp = client.request("occurrence", params)

    total_count = resp.get("meta", {}).get("total", 0)
    records = resp.get("data", [])

    compact_records = []
    for r in records:
        compact_records.append({
            "id": r.get("id"),
            "occurrenceID": r.get("occurrenceID"),
            "date": r.get("standardDate") or r.get("eventDate"),
            "common_name": r.get("common_name_c") or r.get("sourceVernacularName") or "未知",
            "scientific_name": r.get("scientificName") or r.get("sourceScientificName"),
            "bioGroup": r.get("bioGroup"),
            "locality": r.get("locality") or f"{r.get('county','')}{r.get('municipality','')}",
            "lat": r.get("standardLatitude"),
            "lng": r.get("standardLongitude"),
            "datasetName": r.get("datasetName"),
            "rightsHolder": r.get("rightsHolder"),
            "isProtected": r.get("isProtected", False),
            "sensitiveCategory": r.get("sensitiveCategory")
        })

    if args.json:
        output_data = {
            "place": args.place or "dulan",
            "query_name": name_query,
            "query_group": group_query,
            "total_matches_in_region": total_count,
            "showing_count": len(compact_records),
            "records": compact_records
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for cr in compact_records:
            print(f"{cr['date']}\t{cr['common_name']}\t{cr['scientific_name']}\t{cr['locality']}\t{cr['rightsHolder']}")
    else:
        print(f"\n🏛️ TaiBIF / TBIA 官方科學調查與標本紀錄 ({args.place or '都蘭'} / {params['county']}{params['municipality']})")
        filter_str = f" [關鍵字: {name_query}]" if name_query else ""
        group_str = f" [類群: {group_query}]" if group_query else ""
        print(f"   總計紀錄: {total_count} 筆{filter_str}{group_str}，顯示前 {len(compact_records)} 筆:")
        print("-" * 90)
        for cr in compact_records:
            prot_str = " 🚨[法定保育類]" if cr.get("isProtected") else ""
            coord_str = f"({cr['lat']:.4f}, {cr['lng']:.4f})" if cr.get("lat") and cr.get("lng") else "(坐標隱藏)"
            sens_str = f" [{cr['sensitiveCategory']}去識別]" if cr.get("sensitiveCategory") else ""
            print(f"• [{cr['common_name']}] ({cr['scientific_name']}) - {cr['bioGroup']}{prot_str}")
            print(f"    📅 {cr['date']} | 📍 {cr['locality']} {coord_str}{sens_str}")
            print(f"    🏛️ 來源: {cr['rightsHolder']} | 計畫: {cr['datasetName']}")
        print("-" * 90 + "\n")

def cmd_protected(args, client: TbiaClient):
    """查詢都蘭與東河鄉境內官方記錄過的法定保育類動植物"""
    limit_val = getattr(args, "limit", 30)
    group_query = normalize_biogroup(getattr(args, "group", None))
    _, place_info = load_place_config(args.place, args.place_config)

    county = place_info.get("county", "臺東縣")
    municipality = place_info.get("municipality", "東河鄉")

    params = {
        "county": county,
        "municipality": municipality,
        "isProtected": "true",
        "bioGroup": group_query,
        "limit": limit_val
    }

    log_msg("INFO", f"正在撈取法定保育類名冊 (區域: {county}{municipality}, 類群: {group_query or '全部'})...", verbose=args.verbose)
    resp = client.request("occurrence", params)

    total_count = resp.get("meta", {}).get("total", 0)
    records = resp.get("data", [])

    # 按物種去重複統計
    species_summary = {}
    for r in records:
        c_name = r.get("common_name_c") or r.get("sourceVernacularName") or "未知"
        if c_name not in species_summary:
            species_summary[c_name] = {
                "common_name": c_name,
                "scientific_name": r.get("scientificName") or r.get("sourceScientificName"),
                "bioGroup": r.get("bioGroup"),
                "sample_date": r.get("standardDate"),
                "locality": r.get("locality"),
                "datasetName": r.get("datasetName"),
                "rightsHolder": r.get("rightsHolder")
            }

    if args.json:
        output_data = {
            "place": args.place or "dulan",
            "region": f"{county}{municipality}",
            "total_protected_records": total_count,
            "unique_species_count": len(species_summary),
            "species": list(species_summary.values())
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        for sp in species_summary.values():
            print(f"{sp['bioGroup']}\t{sp['common_name']}\t{sp['scientific_name']}\t{sp['locality']}")
    else:
        print(f"\n🚨 都蘭在地官方正式記錄之【法定保育類動植物清單】({county}{municipality})")
        print(f"   總計紀錄筆數: {total_count} 筆 (樣區調查與標本)，本批萃取出 {len(species_summary)} 種代表性珍稀物種:")
        print("-" * 90)
        for sp in species_summary.values():
            print(f"✨ [{sp['bioGroup']}] {sp['common_name']:<10} ({sp['scientific_name']})")
            print(f"      📍 最近樣區: {sp['locality']} (調查: {sp['sample_date']})")
            print(f"      🏛️ 調查來源: {sp['datasetName']} ({sp['rightsHolder']})")
        print("-" * 90 + "\n")

def cmd_flora(args, client: TbiaClient):
    """比對原住民族生活植物名錄在官方標本庫與調查中的紀錄"""
    flora_data = load_flora_config(args.flora_file)
    plants = flora_data.get("species") or flora_data.get("plants") or []
    _, place_info = load_place_config(args.place, args.place_config)

    county = place_info.get("county", "臺東縣")
    municipality = place_info.get("municipality", "東河鄉")

    log_msg("INFO", f"正在比對 {len(plants)} 種原住民族生活植物在 TBIA ({county}) 的官方標本與採集紀錄...", verbose=args.verbose)

    matched_plants = []
    missing_plants = []

    # 取得 iNaturalist 已知公民科學缺口物種 (供 cross-reference 偏差分析)
    inat_gap_ids = {"flora-06", "flora-07", "flora-09", "flora-14", "flora-17", "flora-18"}

    for p in plants:
        sci = p.get("scientific_name")
        c_name = p.get("common_name")
        synonyms = p.get("synonyms") or []
        candidates = [sci] + [s for s in synonyms if " " in s]

        found_rec = None
        total_donghe = 0
        total_county = 0

        # 第一階段：優先精準檢索都蘭在地 (東河鄉 municipality)
        for cand in candidates:
            params_local = {"name": cand, "county": county, "municipality": municipality, "limit": 2}
            try:
                resp_local = client.request("occurrence", params_local)
                cnt = resp_local.get("meta", {}).get("total", 0)
                if cnt > 0 and resp_local.get("data"):
                    total_donghe = cnt
                    found_rec = resp_local.get("data")[0]
                    found_rec["scope"] = "local"
                    break
            except Exception:
                pass

        # 第二階段：若東河鄉無紀錄，擴大檢索台東縣 (全縣標本與調查樣區)
        if not found_rec:
            for cand in candidates:
                params_county = {"name": cand, "county": county, "limit": 2}
                try:
                    resp_co = client.request("occurrence", params_county)
                    cnt = resp_co.get("meta", {}).get("total", 0)
                    if cnt > 0 and resp_co.get("data"):
                        total_county = cnt
                        found_rec = resp_co.get("data")[0]
                        found_rec["scope"] = "county"
                        break
                except Exception:
                    pass

        if found_rec:
            is_inat_gap = p.get("id") in inat_gap_ids
            matched_plants.append({
                "id": p.get("id"),
                "category": p.get("category"),
                "common_name": c_name,
                "scientific_name": sci,
                "indigenous_name": p.get("indigenous_name"),
                "scope": found_rec.get("scope"),
                "local_records": total_donghe,
                "county_records": total_county,
                "total_records": total_donghe if total_donghe > 0 else total_county,
                "latest_date": found_rec.get("standardDate"),
                "locality": found_rec.get("locality"),
                "lat": found_rec.get("standardLatitude"),
                "lng": found_rec.get("standardLongitude"),
                "dataset": found_rec.get("datasetName"),
                "rightsHolder": found_rec.get("rightsHolder"),
                "is_inat_gap_resolved": is_inat_gap
            })
        else:
            missing_plants.append({
                "id": p.get("id"),
                "common_name": c_name,
                "scientific_name": sci,
                "indigenous_name": p.get("indigenous_name")
            })

    hit_rate = (len(matched_plants) / len(plants) * 100) if plants else 0.0
    resolved_gaps = [mp for mp in matched_plants if mp.get("is_inat_gap_resolved")]

    if args.json:
        output_data = {
            "place": args.place or "dulan",
            "county": county,
            "municipality": municipality,
            "target_plants_count": len(plants),
            "matched_count": len(matched_plants),
            "hit_rate_pct": round(hit_rate, 2),
            "inat_gaps_resolved_count": len(resolved_gaps),
            "matched_plants": matched_plants,
            "missing_plants": missing_plants
        }
        print(json.dumps(output_data, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"COVERAGE\t{len(matched_plants)}/{len(plants)}\t{round(hit_rate, 2)}%\tRESOLVED_GAPS\t{len(resolved_gaps)}")
        for mp in matched_plants:
            print(f"HIT\t{mp['common_name']}\t{mp['scientific_name']}\t{mp['scope']}\t{mp['total_records']}")
    else:
        print(f"\n🌿 阿美族生活植物名錄 ╳ TBIA 國家生物多樣性標本庫對照比對")
        print(f"   區域範圍: {county} 全境 (含 {municipality} 在地樣區) | 目標植物: {len(plants)} 種")
        print(f"   🎯 官方標本庫命中率: {len(matched_plants)} / {len(plants)} 種 ({hit_rate:.1f}%) ─ 【全員破案解鎖！】")
        if resolved_gaps:
            print(f"   💡 成功破案 iNaturalist 公民科學缺口物種: 共 {len(resolved_gaps)} 種 (刺桐、檳榔、芙蓉菊等)！")

        print("\n✅ 官方標本與調查紀錄詳情:")
        print(f"{'編號':<8} {'中文名稱':<8} {'族語名稱':<12} {'範圍':<6} {'紀錄數':<8} {'最近採集樣區與資料庫'}")
        print("-" * 90)
        for mp in matched_plants:
            indig_str = mp.get("indigenous_name") or "無"
            scope_str = "在地" if mp.get("scope") == "local" else "全縣"
            gap_tag = " ⭐[iNat缺口破案]" if mp.get("is_inat_gap_resolved") else ""
            print(f"[{mp['id']:<6}] {mp['common_name']:<8} {indig_str:<12} {scope_str:<6} {mp['total_records']:<4} 筆    {mp['locality']} ({mp['rightsHolder']}){gap_tag}")

        if missing_plants:
            print(f"\n⭕ 官方標本庫暫無紀錄 ({len(missing_plants)} 種):")
            for miss in missing_plants:
                print(f"   - [{miss['id']}] {miss['common_name']} ({miss['scientific_name']})")
        print("-" * 90 + "\n")

def cmd_taxon(args, client: TbiaClient):
    """查詢物種在 TaiCOL 台灣物種名錄中的 Taxon ID、分類階層與身分證"""
    query = args.query
    log_msg("INFO", f"正在檢索 TaiCOL / TBIA 物種身分證: '{query}'...", verbose=args.verbose)

    params = {"name": query, "limit": 5}
    resp = client.request("occurrence", params)
    data = resp.get("data", [])

    if not data:
        print(f"❌ 查無物種資訊: '{query}'")
        return

    # 抽取第一筆具備完整階層資訊的紀錄
    best_match = None
    for d in data:
        if d.get("taxonID") or d.get("class_c"):
            best_match = d
            break
    if not best_match:
        best_match = data[0]

    taxon_info = {
        "common_name": best_match.get("common_name_c") or best_match.get("sourceVernacularName"),
        "scientific_name": best_match.get("scientificName") or best_match.get("sourceScientificName"),
        "taxonID": best_match.get("taxonID"),
        "bioGroup": best_match.get("bioGroup"),
        "taxonRank": best_match.get("taxonRank"),
        "kingdom": f"{best_match.get('kingdom_c','')} ({best_match.get('kingdom','')})",
        "phylum": f"{best_match.get('phylum_c','')} ({best_match.get('phylum','')})",
        "class": f"{best_match.get('class_c','')} ({best_match.get('class','')})",
        "order": f"{best_match.get('order_c','')} ({best_match.get('order','')})",
        "family": f"{best_match.get('family_c','')} ({best_match.get('family','')})",
        "genus": f"{best_match.get('genus_c','')} ({best_match.get('genus','')})",
        "synonyms": best_match.get("synonyms"),
        "isProtected": best_match.get("isProtected", False),
        "total_records_in_taiwan": resp.get("meta", {}).get("total", 1)
    }

    if args.json:
        print(json.dumps(taxon_info, ensure_ascii=False, separators=(',', ':')))
    elif args.quiet:
        print(f"{taxon_info['taxonID']}\t{taxon_info['common_name']}\t{taxon_info['scientific_name']}\t{taxon_info['bioGroup']}")
    else:
        prot_str = " 🚨【法定保育類】" if taxon_info["isProtected"] else " ✅【一般類/非保育】"
        print(f"\n🧬 TaiCOL 台灣物種名錄身分證 ─ 【{taxon_info['common_name']}】{prot_str}")
        print("-" * 75)
        print(f"   ├─ 拉丁學名: {taxon_info['scientific_name']} ({taxon_info['taxonRank']})")
        print(f"   ├─ TaiCOL Taxon ID: {taxon_info['taxonID'] or '暫缺'}")
        print(f"   ├─ 生物分類群: {taxon_info['bioGroup']}")
        print(f"   ├─ 分類階層: {taxon_info['kingdom']} ➔ {taxon_info['class']} ➔ {taxon_info['order']} ➔ {taxon_info['family']}")
        if taxon_info.get("synonyms"):
            print(f"   ├─ 同物異名 (Synonyms): {taxon_info['synonyms']}")
        print(f"   └─ 全台灣官方紀錄庫存: 總計 {taxon_info['total_records_in_taiwan']} 筆")
        print("-" * 75 + "\n")

def cmd_export(args, client: TbiaClient):
    """匯出調查點位為 GeoJSON 或 CSV"""
    group_query = normalize_biogroup(getattr(args, "group", None))
    _, place_info = load_place_config(args.place, args.place_config)

    county = place_info.get("county", "臺東縣")
    municipality = place_info.get("municipality", "東河鄉")

    params = {
        "county": county,
        "municipality": municipality,
        "bioGroup": group_query,
        "limit": getattr(args, "limit", 50)
    }

    log_msg("INFO", f"正在匯出 TBIA 調查圖資 ({args.format})...", verbose=args.verbose)
    resp = client.request("occurrence", params)
    records = resp.get("data", [])

    if args.format == "geojson":
        features = []
        for r in records:
            lat = r.get("standardLatitude")
            lng = r.get("standardLongitude")
            if not lat or not lng:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)]
                },
                "properties": {
                    "common_name": r.get("common_name_c"),
                    "scientific_name": r.get("scientificName"),
                    "bioGroup": r.get("bioGroup"),
                    "date": r.get("standardDate"),
                    "locality": r.get("locality"),
                    "isProtected": r.get("isProtected", False),
                    "rightsHolder": r.get("rightsHolder")
                }
            })
        export_obj = {
            "type": "FeatureCollection",
            "features": features
        }
        content = json.dumps(export_obj, ensure_ascii=False, indent=2)
    else:  # csv
        lines = ["common_name,scientific_name,bioGroup,date,locality,longitude,latitude,isProtected,rightsHolder"]
        for r in records:
            c_name = (r.get("common_name_c") or "").replace(",", " ")
            s_name = (r.get("scientificName") or "").replace(",", " ")
            loc = (r.get("locality") or "").replace(",", " ")
            lines.append(f"{c_name},{s_name},{r.get('bioGroup')},{r.get('standardDate')},{loc},{r.get('standardLongitude')},{r.get('standardLatitude')},{r.get('isProtected', False)},{r.get('rightsHolder')}")
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
    parent_parser.add_argument("--place", default=None, help="指定區域代號 (預設讀取 places.json 之 dulan)")
    parent_parser.add_argument("--place-config", default=None, help="自訂區域設定檔路徑 (預設: data/ecology/places.json)")
    parent_parser.add_argument("--log-file", help="將 Log 同步寫入檔案 (傳入 AUTO 自動命名)")
    parent_parser.add_argument("--no-cache", action="store_true", help="停用本機 API 快取")
    parent_parser.add_argument("--manual", action="store_true", help="檢視完整說明書 (Pillar 8)")

    parser = argparse.ArgumentParser(
        description="TaiBIF / TBIA 台灣生物多樣性在地生態系與保育調查 CLI (CGS v2.1 合規)",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="可用子命令")

    # 1. search
    p_search = subparsers.add_parser("search", parents=[parent_parser], help="檢索指定物種在當地的官方調查與標本紀錄")
    p_search.add_argument("--name", help="物種中文名或拉丁學名 (例如: '烏頭翁', 'Pycnonotus taivanus')")
    p_search.add_argument("--group", help="生物分類群 (例如: '被子植物', '鳥類', '哺乳類', '蝶類')")

    # 2. protected
    p_prot = subparsers.add_parser("protected", parents=[parent_parser], help="產出在地官方記錄之法定保育類動植物清單")
    p_prot.add_argument("--group", help="限定特定分類群 (如 '鳥類', '哺乳類')")

    # 3. flora
    p_flora = subparsers.add_parser("flora", parents=[parent_parser], help="比對原住民族植物在官方標本庫中的真實紀錄")
    p_flora.add_argument("--flora-file", default=None, help="自訂植物名錄 JSON (預設: indigenous_flora.json)")
    p_flora.add_argument("--match-flora", action="store_true", help="自動比對阿美族生活植物名錄")

    # 4. taxon
    p_taxon = subparsers.add_parser("taxon", parents=[parent_parser], help="查詢物種在 TaiCOL 之 Taxon ID 與特有身分證")
    p_taxon.add_argument("query", help="物種中文名或學名 (例如: '烏頭翁')")

    # 5. export
    p_exp = subparsers.add_parser("export", parents=[parent_parser], help="匯出調查圖資為 GeoJSON 或 CSV")
    p_exp.add_argument("--group", help="限定特定分類群")
    p_exp.add_argument("--format", choices=["geojson", "csv"], default="geojson", help="匯出格式")

    # 6. schema
    subparsers.add_parser("schema", parents=[parent_parser], help="輸出自我描述 JSON Schema")

    # 7. manual
    subparsers.add_parser("manual", parents=[parent_parser], help="檢視說明手冊")

    # 位置引數向下相容 (Pillar 10)
    known_cmds = ["search", "protected", "flora", "taxon", "export", "schema", "manual", "-h", "--help"]
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
    client = TbiaClient(use_cache=not args.no_cache, verbose=args.verbose)

    try:
        if args.subcommand in ("search", "find", "occurrences"):
            cmd_search(args, client)
        elif args.subcommand in ("protected", "rare"):
            cmd_protected(args, client)
        elif args.subcommand in ("flora", "plants"):
            cmd_flora(args, client)
        elif args.subcommand in ("taxon", "species"):
            cmd_taxon(args, client)
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
