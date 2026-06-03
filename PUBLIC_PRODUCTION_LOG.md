# Public Production Log

## 2026-06-03

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Latest release commit at deployment time: `0b544ce`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Active production deployment: `dpl_8psg5wkZR9F3srmAzgokcejzWzgg`
- Deployment URL: <https://taiwan-insurance-policy-navigator-3mxwbz8e5.vercel.app>
- Target: production
- Status: READY

Review-stage noindex controls:

- HTML meta robots: `noindex,nofollow,noarchive`
- `robots.txt`: `Disallow: /`
- Vercel header: `X-Robots-Tag: noindex, nofollow, noarchive`

Safety remediation:

- First deployment `dpl_CTEEDgjd7hKrmhN14JqUVBmNHzL4` accidentally included local ignored directories because Vercel did not rely on `.gitignore` alone.
- Added `.vercelignore` to exclude `.git/`, `.env*`, `.vercel/`, `work/`, `outputs/`, `tmp/`, and cache directories.
- Redeployed production safely.
- Removed the first deployment.
- Verified old deployment root and raw manifest paths return `404`.
- Verified active production root returns `200` and raw local paths return `404`.
