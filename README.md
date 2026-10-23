# Capitol Journal

News site at https://capitoljournal.media, published by Atlas Media Network, LLC.

- `build.py` generates the static site into `dist/` (Python, Jinja2, Markdown).
- `site.json`: site settings, sections and the photo library.
- `content/articles/`: stories (Markdown + YAML front matter). Created from the newsroom panel at `/admin/` (Decap CMS, editorial workflow: drafts live on `cms/...` branches until published to `main`).
- `content/pages/`: About Us, Editorial Standards, Privacy Notice.
- `data/`: official election results links and poll closing times (each results link is listed only when `verified: true`).
- Netlify builds every push to `main` (`netlify.toml`).

Local build: `pip install -r requirements.txt && python3 build.py`, then serve `dist/`.
