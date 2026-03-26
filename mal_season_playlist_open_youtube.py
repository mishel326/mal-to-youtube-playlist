import argparse
import re
import sys
import time
import webbrowser
import os
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# --- Configuration ---
BASE_URL = "https://myanimelist.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Quota costs
COST_SEARCH = 100
COST_CREATE_PLAYLIST = 50
COST_ADD_ITEM = 50
MAX_QUOTA = 9800 # Margin of safety

EXCLUDED_WORDS = ["Erotica", "Hentai", "Kids"]

stats = {"quota_used": 0, "items_added": 0, "searches_made": 0, "skipped_by_filter": 0, "mal_links_found": 0}

@dataclass
class AnimeEntry:
    title: str
    anime_url: str
    video_page_url: str | None = None

def update_quota(amount):
    stats["quota_used"] += amount
    if stats["quota_used"] > MAX_QUOTA:
        print("\n⚠️ Quota Limit Imminent! Stopping to save progress...")
        return False
    return True

def get_youtube_client():
    client_secrets_file = "client_secrets.json"
    if not os.path.exists(client_secrets_file): return None
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    credentials = flow.run_local_server(port=0)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def search_youtube_trailer(youtube, anime_title):
    if not update_quota(COST_SEARCH): return None
    try:
        stats["searches_made"] += 1
        print(f"  [Search] {anime_title}...")
        res = youtube.search().list(q=f"{anime_title} Official Trailer", part="id", maxResults=1, type="video").execute()
        time.sleep(1) # Safety delay
        if res.get("items"):
            return res["items"][0]["id"]["videoId"]
    except Exception as e:
        print(f"  Error searching: {e}")
    return None

def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")

def extract_valid_entries(html: str):
    valid_entries = []
    # Logic from our successful dry run
    categories = re.findall(r'class="anime-header">(.*?)</div>(.*?)(?=<div class="anime-header"|$)', html, re.S)
    for _, cat_content in categories:
        full_cards = re.findall(r'(<div[^>]+class="[^"]*seasonal-anime[^"]*".*?)(?=<div[^>]+class="[^"]*seasonal-anime[^"]*"|(?<=</div>)\s*</div>\s*</div>|$)', cat_content, re.S)
        for block in full_cards:
            if any(re.search(rf'\b{word}\b', block, re.I) for word in EXCLUDED_WORDS):
                stats["skipped_by_filter"] += 1
                continue
            title_match = re.search(r'link-title">(.*?)</a>', block)
            url_match = re.search(r'href="(https://myanimelist.net/anime/\d+/[^"]+)"', block)
            video_match = re.search(r'href="(https://myanimelist.net/anime/\d+/[^"]+/video[^"]*)"', block)
            if title_match and url_match:
                title = title_match.group(1).strip()
                if not any(e.title == title for e in valid_entries):
                    valid_entries.append(AnimeEntry(title=title, anime_url=url_match.group(1).split('?')[0], video_page_url=video_match.group(1) if video_match else None))
    return valid_entries

def main():
    youtube = get_youtube_client()
    if not youtube: return

    print("Fetching MAL data...")
    html = fetch_html(f"{BASE_URL}/anime/season")
    entries = extract_valid_entries(html)
    print(f"Found {len(entries)} items. Checking MAL for links first...")

    final_video_ids = []
    for entry in entries:
        v_id = None
        # Try finding in MAL page (Free)
        try:
            p_html = fetch_html(entry.video_page_url or entry.anime_url)
            # Improved regex for YT IDs
            m = re.search(r'(?:v=|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})', p_html)
            if m: 
                v_id = m.group(1)
                stats["mal_links_found"] += 1
        except: pass

        # Only Search if MAL failed AND we have quota
        if not v_id and stats["quota_used"] < MAX_QUOTA - 500:
            v_id = search_youtube_trailer(youtube, entry.title)
        
        if v_id: final_video_ids.append(v_id)

    if final_video_ids:
        update_quota(COST_CREATE_PLAYLIST)
        pl_id = youtube.playlists().insert(part="snippet,status", body={
            "snippet": {"title": f"MAL Seasonal {date.today()}"},
            "status": {"privacyStatus": "private"}
        }).execute()["id"]
        
        print(f"Adding videos. (Progress: {len(final_video_ids)} found)...")
        for vid in list(dict.fromkeys(final_video_ids)):
            if not update_quota(COST_ADD_ITEM): break
            try:
                youtube.playlistItems().insert(part="snippet", body={
                    "snippet": {"playlistId": pl_id, "resourceId": {"kind": "youtube#video", "videoId": vid}}
                }).execute()
                stats["items_added"] += 1
                time.sleep(0.5)
            except: break

        print("\n" + "="*35)
        print(f"✅ Summary: Added {stats['items_added']} videos.")
        print(f"🔗 Found in MAL: {stats['mal_links_found']} (Saved Quota!)")
        print(f"🔍 YouTube Searches: {stats['searches_made']}")
        print(f"💰 Quota Used: {stats['quota_used']} / 10000")
        print("="*35)
        webbrowser.open(f"https://www.youtube.com/playlist?list={pl_id}")

if __name__ == "__main__":
    main()