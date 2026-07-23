#!/usr/bin/env python3
"""One-shot 301 redirect via WP bootstrap (AIOSEO / Rank Math / DB fallback)."""
from __future__ import annotations

import argparse
import ftplib
import io
import json
import sys
import urllib.request
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env(root: Path) -> dict[str, str]:
    for name in ("memory/site.env.local", "memory/site.env.local.example"):
        p = root / name
        if p.is_file():
            env: dict[str, str] = {}
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
            return env
    return {}


def build_php(source_path: str, target_path: str) -> str:
    src = source_path.strip()
    tgt = target_path.strip()
    if not src.startswith("/"):
        src = "/" + src
    if not tgt.startswith("/"):
        tgt = "/" + tgt
    return f"""<?php
require __DIR__ . '/wp-load.php';

$source = {json.dumps(src, ensure_ascii=False)};
$target = {json.dumps(tgt, ensure_ascii=False)};
$done = false;

if (class_exists('AIOSEO\\\\Plugin\\\\Pro\\\\Redirects\\\\Api\\\\Redirects')) {{
    try {{
        $api = new AIOSEO\\\\Plugin\\\\Pro\\\\Redirects\\\\Api\\\\Redirects();
        $result = $api->createRedirect([
            'url' => $source,
            'action_data' => ['url' => $target],
            'action_code' => 301,
            'action_type' => 'url',
            'match_type' => 'url',
            'enabled' => true,
        ]);
        if (!is_wp_error($result)) {{
            echo 'OK aioseo_api source=' . $source . ' target=' . $target . PHP_EOL;
            $done = true;
        }}
    }} catch (Throwable $e) {{
        echo 'WARN aioseo_api: ' . $e->getMessage() . PHP_EOL;
    }}
}}

if (!$done && class_exists('AIOSEO\\\\Plugin\\\\Common\\\\Models\\\\Redirect')) {{
    try {{
        $model = new AIOSEO\\\\Plugin\\\\Common\\\\Models\\\\Redirect();
        $model->source_url = $source;
        $model->target_url = $target;
        $model->redirect_type = 301;
        $model->enabled = 1;
        $model->save();
        echo 'OK aioseo_model source=' . $source . ' target=' . $target . PHP_EOL;
        $done = true;
    }} catch (Throwable $e) {{
        echo 'WARN aioseo_model: ' . $e->getMessage() . PHP_EOL;
    }}
}}

if (!$done && class_exists('RankMath\\\\Redirections\\\\DB')) {{
    try {{
        RankMath\\\\Redirections\\\\DB::add([
            'url_to' => $target,
            'header_code' => '301',
            'sources' => [[
                'pattern' => $source,
                'comparison' => 'exact',
            ]],
        ]);
        echo 'OK rank_math source=' . $source . ' target=' . $target . PHP_EOL;
        $done = true;
    }} catch (Throwable $e) {{
        echo 'WARN rank_math: ' . $e->getMessage() . PHP_EOL;
    }}
}}

if (!$done) {{
    global $wpdb;
    $table = $wpdb->prefix . 'aioseo_redirects';
    $exists = $wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $table));
    if ($exists === $table) {{
        $wpdb->insert($table, [
            'source_url' => $source,
            'target_url' => $target,
            'redirect_type' => 301,
            'enabled' => 1,
            'created' => current_time('mysql'),
            'updated' => current_time('mysql'),
        ], ['%s', '%s', '%d', '%d', '%s', '%s']);
        if ($wpdb->insert_id) {{
            echo 'OK aioseo_db id=' . (int) $wpdb->insert_id . ' source=' . $source . ' target=' . $target . PHP_EOL;
            $done = true;
        }} else {{
            echo 'ERR aioseo_db: ' . $wpdb->last_error . PHP_EOL;
        }}
    }}
}}

if (!$done) {{
    echo 'ERR no_redirect_plugin source=' . $source . ' target=' . $target . PHP_EOL;
    exit(1);
}}
"""


def run_via_ftp(env: dict[str, str], php: str, public_base: str) -> str:
    remote = "excalibur-blog-redirect-once.php"
    ftp_root = (env.get("FTP_ROOT") or "/").strip()
    if not ftp_root.startswith("/"):
        ftp_root = "/" + ftp_root
    if not ftp_root.endswith("/"):
        ftp_root += "/"

    ftp = ftplib.FTP()
    ftp.connect(env["FTP_HOST"], int(env.get("FTP_PORT", "21")), timeout=120)
    ftp.login(env["FTP_USER"], env["FTP_PASS"])
    ftp.set_pasv(True)
    ftp.cwd(ftp_root)
    ftp.storbinary(f"STOR {remote}", io.BytesIO(php.encode("utf-8")))
    ftp.quit()

    url = public_base.rstrip("/") + "/" + remote
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "ExcaliburBlogRedirect/1.0"}),
        timeout=30,
    ) as response:
        out = response.read().decode("utf-8", errors="replace")

    ftp = ftplib.FTP()
    ftp.connect(env["FTP_HOST"], int(env.get("FTP_PORT", "21")), timeout=120)
    ftp.login(env["FTP_USER"], env["FTP_PASS"])
    ftp.set_pasv(True)
    ftp.cwd(ftp_root)
    try:
        ftp.delete(remote)
    except ftplib.error_perm:
        pass
    ftp.quit()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Add 301 redirect on naturallift.store")
    ap.add_argument("--source", required=True, help="Old path, e.g. /2026/06/17/old-slug/")
    ap.add_argument("--target", required=True, help="New path, e.g. /2026/06/17/new-slug/")
    args = ap.parse_args()

    root = project_root()
    env = load_env(root)
    public = env.get("PUBLIC_SITE_URL") or "https://naturallift.store"
    php = build_php(args.source, args.target)
    out = run_via_ftp(env, php, public)
    print(out.strip())
    return 0 if out.strip().startswith("OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
