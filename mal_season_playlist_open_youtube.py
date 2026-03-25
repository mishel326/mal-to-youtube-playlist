import argparse
import re
import sys
import time
import webbrowser
import os
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen

# Google API Libraries
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# --- Configuration ---
BASE_URL = "https://myanimelist.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Quota costs (Units)
COST_SEARCH = 100
COST_CREATE_PLAYLIST = 50
COST_ADD_ITEM = 50

# Blacklist words
EXCLUDED_WORDS = ["Erotica", "Hentai", "Kids"]

# Session Stats
stats = {
    "quota_used": 0,
    "items_added": 0,
    "searches_made": 0,
    "skipped_by_filter": 0
}

@dataclass
class AnimeEntry:
    title: str
    anime_url: str
    video_page_url: str | None = None

# --- YouTube API Core ---

def update_quota(amount):
    stats["quota_used"] += amount

def get_youtube_client():
    client_secrets_file = "client_secrets.json"
    if not os.path.exists(client_secrets_file):
        print(f"Error: {client_secrets_file} not found!")
        return None
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    credentials = flow.run_local_server(port=0)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def search_youtube_trailer(youtube, anime_title):
    try:
        update_quota(COST_SEARCH)
        stats["searches_made"] += 1
        print(f"  [Search] {anime_title}...")
        res = youtube.search().list(q=f"{anime_title} Official Trailer", part="id", maxResults=1, type="video").execute()
        if res.get("items"):
            return res["items"][0]["id"]["videoId"]
    except Exception: pass
    return None

# --- Scraper Logic ---

def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")

def extract_valid_entries(html: str):
    valid_entries = []
    # חלוקה לפי קטגוריות MAL
    categories = re.findall(r'class="anime-header">(.*?)</div>(.*?)(?=<div class="anime-header"|$)', html, re.S)
    
    for _, cat_content in categories:
        # חילוץ בלוקים של אנימה
        full_cards = re.findall(r'(<div[^>]+class="[^"]*seasonal-anime[^"]*".*?)(?=<div[^>]+class="[^"]*seasonal-anime[^"]*"|(?<=</div>)\s*</div>\s*</div>|$)', cat_content, re.S)
        
        for block in full_cards:
            # סינון
            if any(re.search(rf'\b{word}\b', block, re.I) for word in EXCLUDED_WORDS):
                stats["skipped_by_filter"] += 1
                continue
            
            title_match = re.search(r'link-title">(.*?)</a>', block)
            url_match = re.search(r'href="(https://myanimelist.net/anime/\d+/[^"]+)"', block)
            video_match = re.search(r'href="(https://myanimelist.net/anime/\d+/[^"]+/video[^"]*)"', block)
            
            if title_match and url_match:
                title = title_match.group(1).strip()
                if not any(e.title == title for e in valid_entries):
                    valid_entries.append(AnimeEntry(
                        title=title,
                        anime_url=url_match.group(1).split('?')[0],
                        video_page_url=video_match.group(1) if video_match else None
                    ))
    return valid_entries

# --- Execution ---

def main():
    youtube = get_youtube_client()
    if not youtube: return

    print("Fetching and filtering MAL data...")
    html = fetch_html(f"{BASE_URL}/anime/season")
    entries = extract_valid_entries(html)
    print(f"Ready to process {len(entries)} items (Skipped {stats['skipped_by_filter']}).")

    final_video_ids = []
    for entry in entries:
        v_id = None
        # שלב 1: ניסיון מתוך MAL
        try:
            p_html = fetch_html(entry.video_page_url or entry.anime_url)
            m = re.search(r"youtube\.com/(?:embed/|watch\?v=)([A-Za-z0-9_-]{11})", p_html)
            if m: v_id = m.group(1)
        except: pass

        # שלב 2: חיפוש ביוטיוב אם נכשל
        if not v_id:
            v_id = search_youtube_trailer(youtube, entry.title)
        
        if v_id: final_video_ids.append(v_id)

    if final_video_ids:
        update_quota(COST_CREATE_PLAYLIST)
        pl_id = youtube.playlists().insert(part="snippet,status", body={
            "snippet": {"title": f"MAL Seasonal {date.today()}"},
            "status": {"privacyStatus": "private"}
        }).execute()["id"]
        
        print(f"Adding {len(final_video_ids)} videos to playlist...")
        for vid in list(dict.fromkeys(final_video_ids)):
            try:
                update_quota(COST_ADD_ITEM)
                youtube.playlistItems().insert(part="snippet", body={
                    "snippet": {"playlistId": pl_id, "resourceId": {"kind": "youtube#video", "videoId": vid}}
                }).execute()
                stats["items_added"] += 1
                time.sleep(0.5)
            except googleapiclient.errors.HttpError as e:
                if e.resp.status == 403:
                    print("\n[!] Limit reached.")
                    break

        print("\n" + "="*35)
        print(f"✅ Success! Added {stats['items_added']} trailers.")
        print(f"📉 Filtered out: {stats['skipped_by_filter']} items.")
        print(f"💰 Quota used: {stats['quota_used']} units.")
        print("="*35)
        webbrowser.open(f"https://www.youtube.com/playlist?list={pl_id}")

if __name__ == "__main__":
    main()