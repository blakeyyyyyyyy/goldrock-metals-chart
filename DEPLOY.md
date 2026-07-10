# Putting the chart live on your site (hands-off)

The chart already shows **live prices** in any browser. The one thing that needs
help is keeping the **historic baseline** current on the public web — that's what
this does, in the cloud, twice a day, with no Mac involved.

## Option A — Cloud auto-deploy (recommended, free, set-and-forget)

1. Create a **GitHub** account (free) if you don't have one.
2. Make a new repo, e.g. `goldrock-metals-chart`, and push this folder to it:
   ```
   cd ~/goldrock-metals-chart
   git init && git add . && git commit -m "GoldRock live metals chart"
   git branch -M main
   git remote add origin https://github.com/<you>/goldrock-metals-chart.git
   git push -u origin main
   ```
3. In the repo: **Settings → Pages → Build and deployment → Source = GitHub Actions**.
4. That's it. The included workflow (`.github/workflows/deploy.yml`) rebuilds and
   republishes twice daily and on demand. Your chart lives at
   `https://<you>.github.io/goldrock-metals-chart/`.
5. **Embed on goldrockmetalexchange.com** — drop this into a Bricks/HTML block:
   ```html
   <iframe src="https://<you>.github.io/goldrock-metals-chart/"
           style="width:100%;height:900px;border:0" loading="lazy"
           title="GoldRock live metals chart"></iframe>
   ```
   (Optional: point a subdomain like `chart.goldrockmetalexchange.com` at Pages via a
   CNAME so the URL is fully on-brand.)

The build runs `build/build.py` with `GOLDROCK_OUT_DIR=public`, so CI publishes into
`public/` without touching your local copy.

## Option B — Your Mac auto-uploads (no GitHub)

Keep the existing twice-daily `launchd` job and add an upload step (SFTP/rsync) to
your web host after each build. Works only while your Mac is on. Tell me your host's
SFTP details and I'll wire it in.

## Price alerts (lead capture)

The alert form on the page works in **email mode** out of the box (opens the
visitor's mail app to `concierge@goldrockmetalexchange.com`). To capture leads
straight into **HubSpot** instead, set `CONFIG.alertsEndpoint` near the top of
`build/template.html` to your HubSpot form-submit URL (or a small webhook), then
rebuild. Ask me and I'll wire it to your HubSpot portal/form IDs.
