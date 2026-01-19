import json
import os
import re
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import markdown
import yaml
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "posts"
TEMPLATES_DIR = ROOT / "templates"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT

POSTS_JSON = DATA_DIR / "posts.json"
TAGS_JSON = DATA_DIR / "tags.json"

PAGE_SIZE = 8

SITE = {
    "name": "Tech Blog",
    "description": "Blog tech su sistemi, sicurezza e sviluppo, con guide pratiche ogni giorno.",
    "author": "Diego",
    "eyebrow": "Firmware - Cybersecurity - Embedded Systems",
    "hero_title": "Technology. Code. Systems.",
    "hero_subtitle": "Articoli pratici su infrastrutture, sicurezza e automazione.",
    "copyright": "2026 Tech Blog - Diego",
    "default_image": "assets/images/chip.svg",
}

ABOUT = {
    "title": "Chi sono",
    "subtitle": "Blog tecnico con focus su sistemi, sicurezza e automazione.",
    "image": "assets/images/author-placeholder.svg",
    "paragraphs": [
        "Sono Diego, sistemista junior e docente di Python. Lavoro in una scuola e gestisco server Linux, storage condivisi, permessi per studenti e una cartella pubblica per le consegne.",
        "In questo blog pubblico guide pratiche, checklist e procedure reali: quello che faccio davvero in laboratorio e in aula. Niente marketing, solo cose utili.",
        "Se vuoi suggerire un argomento puoi aprire una issue sul repository GitHub.",
    ],
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\\s-]", "", text)
    text = re.sub(r"\\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def parse_frontmatter(content: str) -> Tuple[dict, str]:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip()
            return fm, body
    return {}, content


def parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value))


def estimate_read_time(text: str) -> int:
    words = len(re.findall(r"\\w+", text))
    return max(3, round(words / 200))


def rel_root(output_path: Path) -> str:
    parts = output_path.relative_to(ROOT).parts[:-1]
    depth = len(parts)
    if depth == 0:
        return "."
    return "/".join([".."] * depth)


def rel_url(path: str, rel_root_path: str) -> str:
    if rel_root_path == ".":
        return path
    return f"{rel_root_path}/{path}"


def load_posts() -> List[dict]:
    posts = []
    if not CONTENT_DIR.exists():
        return posts

    for md_path in sorted(CONTENT_DIR.glob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        title = str(fm.get("title", "")).strip()
        if not title:
            continue
        slug = str(fm.get("slug") or slugify(title) or md_path.stem)
        tags_raw = fm.get("tags") or []
        if isinstance(tags_raw, str):
            tags_raw = [t.strip() for t in tags_raw.split(",")]
        tags = [slugify(str(t)) for t in tags_raw if str(t).strip()]
        tags = [t for t in tags if t]
        excerpt = str(fm.get("excerpt", "")).strip()
        cover_image = str(fm.get("cover_image") or SITE["default_image"])
        author = str(fm.get("author") or SITE["author"])
        date_value = parse_date(fm.get("date", datetime.now(timezone.utc).date()))

        body_html = markdown.markdown(
            body,
            extensions=["extra", "fenced_code", "tables"],
        )

        read_time = estimate_read_time(body)
        if not excerpt:
            plain = re.sub(r"<[^>]+>", " ", body_html)
            excerpt = " ".join(plain.split()[:32])

        posts.append(
            {
                "title": title,
                "slug": slug,
                "date": date_value,
                "date_str": date_value.strftime("%Y-%m-%d"),
                "excerpt": excerpt,
                "cover_image": cover_image,
                "author": author,
                "tags": tags,
                "content_html": body_html,
                "read_time": read_time,
            }
        )

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build_tags(posts: List[dict]) -> Dict[str, dict]:
    tag_map: Dict[str, dict] = {}
    for post in posts:
        for tag in post["tags"]:
            if tag not in tag_map:
                tag_map[tag] = {"count": 0, "posts": []}
            tag_map[tag]["count"] += 1
            tag_map[tag]["posts"].append(post)
    return tag_map


def ensure_dirs():
    (OUTPUT_DIR / "articles").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "categories").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tag").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "article").mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def build_meta(site_base: str, title: str, description: str, canonical_path: str, og_type: str, image_path: str, json_ld: str) -> dict:
    canonical = f"{site_base}{canonical_path}"
    image = f"{site_base}/{image_path}" if image_path else ""
    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "og_type": og_type,
        "image": image,
        "json_ld": json_ld,
    }


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    load_dotenv(ROOT / ".env")
    ensure_dirs()

    site_base = os.getenv("SITE_BASE_URL", "https://example.com").rstrip("/")
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )

    posts = load_posts()
    tag_map = build_tags(posts)

    tags_sorted = sorted(
        [
            {
                "slug": slug,
                "label": slug.replace("-", " ").title(),
                "count": data["count"],
            }
            for slug, data in tag_map.items()
        ],
        key=lambda t: t["count"],
        reverse=True,
    )

    pages_for_sitemap = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def nav_links_for(rel_root_path: str) -> dict:
        return {
            "home": rel_url("index.html", rel_root_path),
            "articles": rel_url("articles/index.html", rel_root_path),
            "categories": rel_url("categories/index.html", rel_root_path),
            "about": rel_url("chi-siamo.html", rel_root_path),
            "contact": f"{rel_url('index.html', rel_root_path)}#contact",
        }

    def render(template_name: str, output_path: Path, context: dict):
        template = env.get_template(template_name)
        content = template.render(**context)
        write_file(output_path, content)

    def post_view(post: dict, rel_root_path: str) -> dict:
        return {
            "title": post["title"],
            "excerpt": post["excerpt"],
            "date": post["date_str"],
            "author": post["author"],
            "read_time": post["read_time"],
            "image_url": rel_url(post["cover_image"], rel_root_path),
            "image_alt": post["title"],
            "url": rel_url(f"article/{post['slug']}/index.html", rel_root_path),
            "tags": [
                {
                    "slug": tag,
                    "label": tag.replace("-", " ").title(),
                    "url": rel_url(f"tag/{tag}/index.html", rel_root_path),
                }
                for tag in post["tags"]
            ],
        }

    # Index
    index_path = OUTPUT_DIR / "index.html"
    index_rel_root = rel_root(index_path)
    index_meta = build_meta(
        site_base,
        f"{SITE['name']} | Home",
        SITE["description"],
        "/",
        "website",
        SITE["default_image"],
        json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": SITE["name"],
                "url": f"{site_base}/",
                "description": SITE["description"],
            }
        ),
    )
    render(
        "index.html",
        index_path,
        {
            "site": SITE,
            "asset_base": rel_url("assets", index_rel_root),
            "nav_links": nav_links_for(index_rel_root),
            "nav_active": "home",
            "meta": index_meta,
            "latest_posts": [post_view(p, index_rel_root) for p in posts[:3]],
            "trending_posts": [post_view(p, index_rel_root) for p in posts[:5]],
            "tags": [
                {
                    "label": t["label"],
                    "count": t["count"],
                    "url": rel_url(f"tag/{t['slug']}/index.html", index_rel_root),
                }
                for t in tags_sorted
            ],
            "hero_panel": [
                "New: checklist affidabilita PCB",
                "Hardening per server locali",
                "Zero downtime update in laboratorio",
            ],
        },
    )
    pages_for_sitemap.append((f"{site_base}/", today))

    # Articles pages with pagination
    total_pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)
    for page in range(1, total_pages + 1):
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_posts = posts[start:end]
        if page == 1:
            page_root = "articles/index.html"
            canonical_path = "/articles/"
        else:
            page_root = f"articles/page/{page}/index.html"
            canonical_path = f"/articles/page/{page}/"

        output_path = OUTPUT_DIR / page_root
        rel_root_path = rel_root(output_path)

        pagination = None
        if total_pages > 1:
            prev_url = None
            next_url = None
            if page > 1:
                prev_root = "articles/index.html" if page == 2 else f"articles/page/{page - 1}/index.html"
                prev_url = rel_url(prev_root, rel_root_path)
            if page < total_pages:
                next_root = f"articles/page/{page + 1}/index.html"
                next_url = rel_url(next_root, rel_root_path)
            pagination = {
                "current": page,
                "total": total_pages,
                "prev_url": prev_url,
                "next_url": next_url,
            }

        meta = build_meta(
            site_base,
            f"Articles | Page {page}",
            "Archivio articoli tech con guide pratiche e checklist.",
            canonical_path,
            "website",
            SITE["default_image"],
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "CollectionPage",
                    "name": "Articles",
                    "url": f"{site_base}{canonical_path}",
                }
            ),
        )

        render(
            "articles.html",
            output_path,
            {
                "site": SITE,
                "asset_base": rel_url("assets", rel_root_path),
                "nav_links": nav_links_for(rel_root_path),
                "nav_active": "articles",
                "meta": meta,
                "page_title": "Articles",
                "page_subtitle": "Tutti gli articoli pubblicati, ordinati per data.",
                "posts": [post_view(p, rel_root_path) for p in page_posts],
                "pagination": pagination,
            },
        )
        pages_for_sitemap.append((f"{site_base}{canonical_path}", today))

    # Categories page
    categories_path = OUTPUT_DIR / "categories" / "index.html"
    categories_rel_root = rel_root(categories_path)
    categories_meta = build_meta(
        site_base,
        "Categories",
        "Elenco categorie e tag aggiornati automaticamente.",
        "/categories/",
        "website",
        SITE["default_image"],
        json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Categories",
                "url": f"{site_base}/categories/",
            }
        ),
    )
    render(
        "categories.html",
        categories_path,
        {
            "site": SITE,
            "asset_base": rel_url("assets", categories_rel_root),
            "nav_links": nav_links_for(categories_rel_root),
            "nav_active": "categories",
            "meta": categories_meta,
            "tags": [
                {
                    "label": t["label"],
                    "count": t["count"],
                    "url": rel_url(f"tag/{t['slug']}/index.html", categories_rel_root),
                }
                for t in tags_sorted
            ],
        },
    )
    pages_for_sitemap.append((f"{site_base}/categories/", today))

    # About page
    about_path = OUTPUT_DIR / "chi-siamo.html"
    about_rel_root = rel_root(about_path)
    about_meta = build_meta(
        site_base,
        "About | Tech Blog",
        "Chi sono e come scrivo gli articoli del Tech Blog.",
        "/chi-siamo.html",
        "website",
        SITE["default_image"],
        json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": "About",
                "url": f"{site_base}/chi-siamo.html",
            }
        ),
    )
    render(
        "about.html",
        about_path,
        {
            "site": SITE,
            "asset_base": rel_url("assets", about_rel_root),
            "nav_links": nav_links_for(about_rel_root),
            "nav_active": "about",
            "meta": about_meta,
            "about_title": ABOUT["title"],
            "about_subtitle": ABOUT["subtitle"],
            "about_image": rel_url(ABOUT["image"], about_rel_root),
            "about_paragraphs": ABOUT["paragraphs"],
        },
    )
    pages_for_sitemap.append((f"{site_base}/chi-siamo.html", today))

    # Tag pages
    for tag in tags_sorted:
        tag_slug = tag["slug"]
        tag_path = OUTPUT_DIR / "tag" / tag_slug / "index.html"
        tag_rel_root = rel_root(tag_path)
        canonical_path = f"/tag/{tag_slug}/"
        tag_meta = build_meta(
            site_base,
            f"Tag: {tag['label']}",
            f"Articoli con tag {tag['label']}.",
            canonical_path,
            "website",
            SITE["default_image"],
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "CollectionPage",
                    "name": f"Tag: {tag['label']}",
                    "url": f"{site_base}{canonical_path}",
                }
            ),
        )
        render(
            "tag.html",
            tag_path,
            {
                "site": SITE,
                "asset_base": rel_url("assets", tag_rel_root),
                "nav_links": nav_links_for(tag_rel_root),
                "nav_active": "categories",
                "meta": tag_meta,
                "tag": {
                    "label": tag["label"],
                    "count": tag["count"],
                },
                "posts": [post_view(p, tag_rel_root) for p in tag_map[tag_slug]["posts"]],
            },
        )
        pages_for_sitemap.append((f"{site_base}{canonical_path}", today))

    # Article pages
    for post in posts:
        article_root = f"article/{post['slug']}/index.html"
        article_path = OUTPUT_DIR / article_root
        article_rel_root = rel_root(article_path)
        canonical_path = f"/article/{post['slug']}/"
        blog_json_ld = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post["title"],
            "datePublished": post["date"].strftime("%Y-%m-%d"),
            "dateModified": post["date"].strftime("%Y-%m-%d"),
            "author": {"@type": "Person", "name": SITE["author"]},
            "image": f"{site_base}/{post['cover_image']}",
            "keywords": post["tags"],
            "mainEntityOfPage": f"{site_base}{canonical_path}",
        }
        breadcrumbs = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{site_base}/"},
                {"@type": "ListItem", "position": 2, "name": "Articles", "item": f"{site_base}/articles/"},
                {"@type": "ListItem", "position": 3, "name": post["title"], "item": f"{site_base}{canonical_path}"},
            ],
        }
        article_meta = build_meta(
            site_base,
            post["title"],
            post["excerpt"],
            canonical_path,
            "article",
            post["cover_image"],
            json.dumps([blog_json_ld, breadcrumbs]),
        )
        render(
            "article.html",
            article_path,
            {
                "site": SITE,
                "asset_base": rel_url("assets", article_rel_root),
                "nav_links": nav_links_for(article_rel_root),
                "nav_active": "articles",
                "meta": article_meta,
                "post": {
                    **post_view(post, article_rel_root),
                    "content_html": post["content_html"],
                },
            },
        )
        pages_for_sitemap.append((f"{site_base}{canonical_path}", post["date"].strftime("%Y-%m-%d")))

    # Data files
    posts_payload = {
        "version": 2,
        "posts": [
            {
                "title": p["title"],
                "summary": p["excerpt"],
                "date": p["date_str"],
                "read_minutes": p["read_time"],
                "author": p["author"],
                "tags": p["tags"],
                "image": p["cover_image"],
                "path": f"article/{p['slug']}/index.html",
                "slug": p["slug"],
            }
            for p in posts
        ],
    }
    write_file(POSTS_JSON, json.dumps(posts_payload, ensure_ascii=False, indent=2))

    tags_payload = {
        "version": 1,
        "tags": [
            {
                "tag": t["slug"],
                "label": t["label"],
                "count": t["count"],
                "path": f"tag/{t['slug']}/index.html",
            }
            for t in tags_sorted
        ],
    }
    write_file(TAGS_JSON, json.dumps(tags_payload, ensure_ascii=False, indent=2))

    # Robots and sitemap
    robots = f"User-agent: *\\nAllow: /\\nSitemap: {site_base}/sitemap.xml\\n"
    write_file(OUTPUT_DIR / "robots.txt", robots)

    sitemap_items = []
    for loc, lastmod in pages_for_sitemap:
        sitemap_items.append(
            f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>"
        )
    sitemap = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        + "".join(sitemap_items)
        + "</urlset>"
    )
    write_file(OUTPUT_DIR / "sitemap.xml", sitemap)


if __name__ == "__main__":
    main()
