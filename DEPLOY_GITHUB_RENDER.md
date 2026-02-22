# Deploy With GitHub + Render

## 1) Initialize Git and push to GitHub

Run these commands from the project folder:

```powershell
git init
git add .
git commit -m "Initial deploy-ready version"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

If the repo already exists locally, skip `git init` and just push.

## 2) Deploy on Render

1. Open `https://dashboard.render.com/`
2. Click `New +` -> `Blueprint`
3. Connect your GitHub account and select this repository.
4. Render detects `render.yaml` and creates the web service.
5. Click `Apply`.

After build completes, open the generated Render URL.

## 3) Verify production

Check:

- `GET /api/health` returns `{ "ok": true, "data": { "status": "ok" } }`
- Upload and analyze a sample CSV/TXT
- Search and PDF export both work

## 4) Future updates

Any push to `main` triggers automatic redeploy.

```powershell
git add .
git commit -m "Update app"
git push
```
