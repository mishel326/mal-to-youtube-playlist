# MAL to YouTube Seasonal Playlist 📺🌸

An automated Python tool that scrapes **MyAnimeList** seasonal pages, filters out unwanted content (Kids, Hentai, Erotica), and generates a permanent trailer playlist directly in your **YouTube account**.

## ✨ Features
* **Smart Filtering:** Automatically skips anime categorized as *Kids*, *Hentai*, or *Erotica* based on MAL demographics and genres.
* **Quota Efficient:** Attempts to extract official trailer IDs directly from the MAL page before resorting to a YouTube search, saving API units.
* **Deep Scan:** Scans all seasonal categories including TV, ONA, Movies, and Specials.
* **Auto-Playlist:** Creates a private playlist in your YouTube library and opens it in your browser once finished.
* **Session Summary:** Provides a detailed breakdown of skipped items and API quota used after every run.

## 🛠 Prerequisites
1.  **Google Cloud Project:** Enable the **YouTube Data API v3** in the [Google Cloud Console](https://console.cloud.google.com/).
2.  **OAuth Credentials:** Create a "Desktop App" OAuth Client ID and download the JSON file.
3.  **Local Setup:** Rename the downloaded JSON to `client_secrets.json` and place it in the project folder.
4.  **Python Libraries:**
    ```bash
    pip install google-auth-oauthlib google-api-python-client
    ```

## 🚀 How to Use
1.  Ensure `client_secrets.json` is in the same directory as the script.
2.  Run the script:
    ```bash
    python mal_season_playlist_open_youtube.py
    ```
3.  A browser window will open asking for permission to manage your YouTube account. Log in and authorize the app.
4.  Wait for the script to finish. It will print a summary and open your new playlist.

## ⚠️ Important Notes
* **Security:** Never upload `client_secrets.json` or `token.json` to GitHub. They are already included in the `.gitignore` provided in this repo.
* **API Quotas:** YouTube provides a free daily quota of 10,000 units. A typical run for one season uses approximately 2,000–6,000 units depending on how many trailers need to be searched manually.
* **Test Users:** Ensure you have added your email address as a "Test User" in the OAuth Consent Screen settings on Google Cloud.

---
