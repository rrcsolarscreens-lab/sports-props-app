# Make this a mobile app

## Fastest way: Streamlit Cloud (free public link you can install)

1. Create a free GitHub account if you don't have one
2. Upload this `sports_props_app` folder to a new public repository
3. Go to https://share.streamlit.io and sign in with GitHub
4. Click "New app"
5. Select your repo, set main file path to `ui.py`
6. Click "Advanced settings" → Secrets and add:
   ```
   ODDS_API_KEY = "your_key_here"
   ```
7. Deploy

You'll get a link like `https://yourname-props.streamlit.app`

### Install on iPhone
1. Open the link in Safari
2. Tap the Share button
3. Tap "Add to Home Screen"
4. It now opens like a normal app (full screen, no browser bars)

## Local testing
```bash
streamlit run ui.py
```
Then on your phone (same Wi-Fi) use the Network URL shown in the terminal.
