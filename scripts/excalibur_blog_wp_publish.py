#!/usr/bin/env python3
"""Publish one Excalibur blog article to WordPress (FTP bootstrap)."""
from __future__ import annotations

import argparse
import base64
import ftplib
import io
import json
import sys
import urllib.request
from pathlib import Path

from asset_download import download_url_bytes
from excalibur_blog_article_format import format_article_html
from excalibur_env import assert_naturallift_publish_target, load_env
from excalibur_repo_paths import repo_relative
from image_validate import sniff_image_format, validate_image_file


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cover_url_from_registry(registry_path: Path) -> str:
    if not registry_path.is_file():
        return ""
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for key in ("transparent_url", "remote_packaged_url", "packaged_url", "attachment_url", "url", "cover_url", "image_url"):
        value = str(registry.get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    return ""


def normalize_cover_png(cover_path: Path, registry_path: Path, root: Path) -> dict[str, object]:
    evidence: dict[str, object] = {
        "path": repo_relative(cover_path, root),
        "source": "existing_file",
        "decode_verified": False,
    }
    errors = validate_image_file(cover_path) if cover_path.is_file() else [f"missing cover file: {cover_path}"]

    if errors:
        remote_url = cover_url_from_registry(registry_path)
        if not remote_url:
            raise RuntimeError("; ".join(errors) + "; no remote cover URL in cover-registry.json")
        data, remote_evidence = download_url_bytes(remote_url, timeout=20, retries=6, chunk_size=8 * 1024)
        detected = sniff_image_format(data)
        if not detected:
            raise RuntimeError("downloaded cover bytes are not a known image format")
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cover_path.with_name(f"{cover_path.stem}.tmp{cover_path.suffix}")
        try:
            if detected == "png":
                tmp.write_bytes(data)
            elif detected in {"webp", "jpeg", "gif"}:
                from PIL import Image

                with Image.open(io.BytesIO(data)) as image:
                    image.save(tmp, format="PNG")
            else:
                raise RuntimeError(f"unsupported cover format: {detected}")
            cover_errors = validate_image_file(tmp)
            if cover_errors:
                raise RuntimeError("; ".join(cover_errors))
            tmp.replace(cover_path)
        finally:
            tmp.unlink(missing_ok=True)
        evidence.update(
            {
                "source": "range_download",
                "remote_url": remote_url,
                "remote_content_type": remote_evidence.get("content_type"),
                "remote_content_range": remote_evidence.get("content_range"),
                "remote_signature_hex": remote_evidence.get("signature_hex"),
                "downloaded_bytes": len(data),
                "detected_remote_format": detected,
            }
        )

    final_errors = validate_image_file(cover_path)
    if final_errors:
        raise RuntimeError("; ".join(final_errors))
    if sniff_image_format(cover_path.read_bytes()) != "png":
        raise RuntimeError(f"cover must be a real PNG after normalization: {cover_path}")

    evidence.update(
        {
            "bytes": cover_path.stat().st_size,
            "detected_format": "png",
            "decode_verified": True,
        }
    )
    return evidence


def load_article(article_dir: Path) -> dict:
    meta_path = article_dir / "article.meta.json"
    html_path = article_dir / "article.html"
    if not meta_path.is_file() or not html_path.is_file():
        raise FileNotFoundError("article.meta.json and article.html required")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    content = format_article_html(html_path.read_text(encoding="utf-8").strip())
    cover_path = article_dir / "cover" / "cover.png"
    schema_path = article_dir / "schema.jsonld"
    cover_b64 = ""
    cover_evidence: dict[str, object] = {}
    cover_reg = article_dir / "cover" / "cover-registry.json"
    if cover_path.is_file():
        cover_evidence = normalize_cover_png(cover_path, cover_reg, project_root())
        cover_b64 = base64.b64encode(cover_path.read_bytes()).decode("ascii")
    schema_raw = ""
    if schema_path.is_file():
        schema_raw = schema_path.read_text(encoding="utf-8").strip()
    cover_alt = meta.get("cover_alt") or meta.get("cover_alt_text") or ""
    if cover_reg.is_file():
        reg = json.loads(cover_reg.read_text(encoding="utf-8"))
        cover_alt = cover_alt or reg.get("cover_alt_text") or reg.get("alt", "")
        if not cover_alt:
            for asset in reg.get("assets") or []:
                if asset.get("role") == "cover" and asset.get("alt"):
                    cover_alt = asset["alt"]
                    break

    import re
    img_tags = re.findall(r"<img\s+[^>]*>", content, flags=re.I)
    inline_images = []
    for tag in img_tags:
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag, flags=re.I)
        if not src_m:
            continue
        src = src_m.group(1)
        alt_m = re.search(r'alt=["\']([^"\']*)["\']', tag, flags=re.I)
        alt_text = alt_m.group(1) if alt_m else ""
        if not src.startswith(("http://", "https://", "data:")):
            local_path = article_dir / src
            if local_path.is_file():
                img_bytes = local_path.read_bytes()
                b64_data = base64.b64encode(img_bytes).decode("ascii")
                inline_images.append({
                    "src": src,
                    "b64": b64_data,
                    "filename": local_path.name,
                    "alt": alt_text,
                })

    meta_ab = meta.get("meta_ab") or {}
    excerpt = meta.get("description") or meta_ab.get("description_seo") or ""
    seo_title = meta_ab.get("title_seo") or meta.get("title") or meta.get("h1", "")
    seo_description = meta_ab.get("description_seo") or excerpt
    focus_keyword = meta.get("focus_keyword") or meta_ab.get("focus_keyword") or meta.get("primary_query") or ""

    return {
        "slug": meta["slug"],
        "title": meta.get("title") or meta.get("h1", ""),
        "excerpt": excerpt,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "focus_keyword": focus_keyword,
        "content": content,
        "cover_b64": cover_b64,
        "cover_evidence": cover_evidence,
        "cover_alt": cover_alt,
        "schema_jsonld": schema_raw,
        "topic_id": meta.get("topic_id", ""),
        "inline_images": inline_images,
        "post_status": meta.get("post_status", "publish"),
    }


def build_php(payload: dict) -> str:
    b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return f"""<?php
require __DIR__ . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/post.php';

$p = json_decode(base64_decode('{b64}'), true);
$slug = $p['slug'];
$existing = get_page_by_path($slug, OBJECT, 'post');
if ($existing instanceof WP_Post) {{
    $post_id = (int) $existing->ID;
    wp_update_post([
        'ID' => $post_id,
        'post_title' => $p['title'],
        'post_name' => $slug,
        'post_content' => $p['content'],
        'post_excerpt' => $p['excerpt'],
        'post_status' => $p['post_status'] ?? 'publish',
    ]);
}} else {{
    $post_id = (int) wp_insert_post([
        'post_title' => $p['title'],
        'post_name' => $slug,
        'post_content' => $p['content'],
        'post_excerpt' => $p['excerpt'],
        'post_status' => $p['post_status'] ?? 'publish',
        'post_type' => 'post',
    ], true);
}}
if (is_wp_error($post_id)) {{
    echo 'ERR post: ' . $post_id->get_error_message() . PHP_EOL;
    exit(1);
}}
echo 'OK post=' . $post_id . ' slug=' . $slug . PHP_EOL;

if (!empty($p['cover_b64'])) {{
    $bin = base64_decode($p['cover_b64']);
    $tmp = wp_tempnam('excalibur-cover-' . $slug . '.png');
    file_put_contents($tmp, $bin);
    $file_array = [
        'name' => $slug . '-cover.png',
        'tmp_name' => $tmp,
        'type' => 'image/png',
        'error' => 0,
        'size' => strlen($bin),
    ];
    $att_id = media_handle_sideload($file_array, $post_id, null, [
        'post_title' => $slug . ' cover',
    ]);
    if (is_wp_error($att_id)) {{
        echo 'WARN cover: ' . $att_id->get_error_message() . PHP_EOL;
    }} else {{
        set_post_thumbnail($post_id, (int) $att_id);
        if (!empty($p['cover_alt'])) {{
            update_post_meta((int) $att_id, '_wp_attachment_image_alt', sanitize_text_field($p['cover_alt']));
        }}
        echo 'OK featured_image=' . (int) $att_id . PHP_EOL;
    }}
    @unlink($tmp);
}}

if (!empty($p['schema_jsonld'])) {{
    update_post_meta($post_id, '_excalibur_blog_schema_jsonld', wp_slash($p['schema_jsonld']));
    update_post_meta($post_id, '_excalibur_blog_skip_theme_faq', '1');
    echo 'OK schema_meta=1' . PHP_EOL;
    echo 'OK skip_theme_faq_meta=1' . PHP_EOL;
}}

if (!empty($p['seo_title']) || !empty($p['seo_description']) || !empty($p['focus_keyword'])) {{
    if (!empty($p['seo_title'])) {{
        update_post_meta($post_id, 'rank_math_title', sanitize_text_field($p['seo_title']));
        update_post_meta($post_id, '_yoast_wpseo_title', sanitize_text_field($p['seo_title']));
    }}
    if (!empty($p['seo_description'])) {{
        update_post_meta($post_id, 'rank_math_description', sanitize_textarea_field($p['seo_description']));
        update_post_meta($post_id, '_yoast_wpseo_metadesc', sanitize_textarea_field($p['seo_description']));
    }}
    if (!empty($p['focus_keyword'])) {{
        update_post_meta($post_id, 'rank_math_focus_keyword', sanitize_text_field($p['focus_keyword']));
        update_post_meta($post_id, '_yoast_wpseo_focuskw', sanitize_text_field($p['focus_keyword']));
    }}
    echo 'OK seo_meta=1 title=' . strlen($p['seo_title'] ?? '') . ' desc=' . strlen($p['seo_description'] ?? '') . PHP_EOL;
}}

if (!empty($p['inline_images'])) {{
    $content_updated = $p['content'];
    foreach ($p['inline_images'] as $img) {{
        $bin = base64_decode($img['b64']);
        $filename = $img['filename'];
        $src = $img['src'];
        
        $tmp = wp_tempnam('excalibur-inline-' . $slug . '-' . sanitize_title($filename));
        file_put_contents($tmp, $bin);
        
        $file_array = [
            'name' => $slug . '-' . $filename,
            'tmp_name' => $tmp,
            'type' => 'image/png',
            'error' => 0,
            'size' => strlen($bin),
        ];
        
        $att_id = media_handle_sideload($file_array, $post_id, null, [
            'post_title' => $slug . ' ' . pathinfo($filename, PATHINFO_FILENAME),
        ]);
        
        if (is_wp_error($att_id)) {{
            echo 'WARN inline_img_upload: ' . $att_id->get_error_message() . ' for ' . $src . PHP_EOL;
        }} else {{
            if (!empty($img['alt'])) {{
                update_post_meta((int) $att_id, '_wp_attachment_image_alt', sanitize_text_field($img['alt']));
            }}
            $new_url = wp_get_attachment_url((int) $att_id);
            if ($new_url) {{
                $content_updated = str_replace('src="' . $src . '"', 'src="' . $new_url . '"', $content_updated);
                $content_updated = str_replace("src='" . $src . "'", "src='" . $new_url . "'", $content_updated);
                echo 'OK inline_image_upload=' . (int) $att_id . ' src=' . $src . ' url=' . $new_url . PHP_EOL;
            }}
        }}
        @unlink($tmp);
    }}
    wp_update_post([
        'ID' => $post_id,
        'post_content' => $content_updated,
    ]);
}}

$permalink = get_permalink($post_id);
echo 'permalink=' . $permalink . PHP_EOL;
"""


def publish_via_ftp(env: dict[str, str], php: str, public_base: str) -> str:
    remote = "excalibur-blog-publish-once.php"
    ftp_root = (env.get("FTP_ROOT") or env.get("FTP_PATH") or "/").strip()
    if not ftp_root.startswith("/"):
        ftp_root = "/" + ftp_root
    if not ftp_root.endswith("/"):
        ftp_root += "/"

    def ftp_connect() -> ftplib.FTP:
        ftp = ftplib.FTP()
        ftp.connect(env["FTP_HOST"], int(env.get("FTP_PORT", "21")), timeout=120)
        ftp.login(env["FTP_USER"], env["FTP_PASS"])
        ftp.set_pasv(True)
        ftp.cwd(ftp_root)
        return ftp

    ftp = ftp_connect()
    ftp.storbinary(f"STOR {remote}", io.BytesIO(php.encode("utf-8")))
    ftp.quit()

    url = public_base.rstrip("/") + "/" + remote
    out = ""
    try:
        print(f"Triggering HTTP publish on {url}...")
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "ExcaliburBlogPublish/1.0"}),
            timeout=15,
        ) as response:
            out = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Local HTTP trigger failed ({type(e).__name__}: {e}). Entering Cloud WebFetch Fallback mode...")
        print(f"=== FALLBACK_TRIGGER_URL ===\n{url}\n=============================")
        print("Waiting for cloud-agent to write response to memory/webfetch-response.txt...")
        
        fallback_file = project_root() / "memory" / "webfetch-response.txt"
        fallback_file.unlink(missing_ok=True)
        
        import time
        for i in range(120):
            if fallback_file.is_file():
                out = fallback_file.read_text(encoding="utf-8")
                fallback_file.unlink()
                print("Cloud response detected successfully!")
                break
            time.sleep(1)
        
        if not out:
            raise RuntimeError("Cloud WebFetch Fallback timed out after 120 seconds. Please trigger manually.")

    ftp = ftp_connect()
    try:
        ftp.delete(remote)
    except ftplib.error_perm:
        pass
    ftp.quit()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--public-base", type=str, default=None, help="Override PUBLIC_SITE_URL")
    ap.add_argument("--draft", action="store_true", help="WP post_status=draft (не публиковать)")
    ap.add_argument(
        "--skip-wordstat-gate",
        action="store_true",
        help="Не проверять Wordstat gate (только аварийно)",
    )
    args = ap.parse_args()
    root = project_root()
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    env = load_env(root)
    draft = args.draft or env.get("EXCALIBUR_BLOG_PUBLISH_DRAFT", "").strip().lower() in (
        "yes",
        "1",
        "true",
    )
    if draft and not args.draft:
        print("INFO: EXCALIBUR_BLOG_PUBLISH_DRAFT=yes → post_status=draft")

    if not args.skip_wordstat_gate and not args.dry_run:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from excalibur_blog_wordstat_gate import gate_article as wordstat_gate

        policy_path = root / "memory/brief/editorial-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        ws_report = wordstat_gate(article_dir, policy, fetch_missing=True)
        print(f"wordstat gate: {ws_report['status']}")
        for err in ws_report.get("errors") or []:
            print(f"  ERROR: {err}", file=sys.stderr)
        for warn in ws_report.get("warnings") or []:
            print(f"  WARN: {warn}", file=sys.stderr)
        if ws_report["status"] != "PASS":
            print("BLOCKER: WORDSTAT GATE — исправь title/primary или research-wordstat.json", file=sys.stderr)
            return 3

    payload = load_article(article_dir)
    if draft:
        payload["post_status"] = "draft"
    php = build_php(payload)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "slug": payload["slug"], "title": payload["title"]}, ensure_ascii=False, indent=2))
        print("PHP bytes:", len(php.encode("utf-8")))
        return 0

    env = load_env(root)
    allow = env.get("EXCALIBUR_BLOG_ALLOW_PUBLISH", "").strip().lower()
    if allow != "yes":
        print(f"BLOCKER: EXCALIBUR_BLOG_ALLOW_PUBLISH={allow!r} (нужно латинское yes)", file=sys.stderr)
        return 1
    public = args.public_base or env.get("PUBLIC_SITE_URL") or env.get("WP_HOME") or ""
    if not public:
        print("PUBLIC_SITE_URL or --public-base required", file=sys.stderr)
        return 2
    try:
        assert_naturallift_publish_target(public)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    if not env.get("FTP_HOST") or not env.get("FTP_USER") or not env.get("FTP_PASS"):
        print("BLOCKER: FTP_HOST / FTP_USER / FTP_PASS не заданы (Secrets или site.env.local)", file=sys.stderr)
        return 5
    out = publish_via_ftp(env, php, public)
    print(out)

    result_path = article_dir / "wp-publish-result.json"
    permalink = ""
    for line in out.splitlines():
        if line.startswith("permalink="):
            permalink = line.split("=", 1)[1].strip()
    result = {
        "slug": payload["slug"],
        "topic_id": payload["topic_id"],
        "permalink": permalink,
        "cover_evidence": payload.get("cover_evidence", {}),
        "raw_output": out,
        "verdict": "pass" if "OK post=" in out else "fail",
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
