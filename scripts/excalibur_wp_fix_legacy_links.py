#!/usr/bin/env python3
"""One-time FTP fix: replace page-quiz and dated rasslabit URLs in all WP posts/pages."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from excalibur_blog_wp_publish import load_env, publish_via_ftp  # noqa: E402

PHP = r"""<?php
require __DIR__ . '/wp-load.php';

$replacements = [
    '/page-quiz/' => 'https://naturallift.store/diagnostika-kozhi/',
    'https://naturallift.store/page-quiz/' => 'https://naturallift.store/diagnostika-kozhi/',
    'http://naturallift.store/page-quiz/' => 'https://naturallift.store/diagnostika-kozhi/',
    'https://naturallift.store/2026/05/26/kak-rasslabit-liczo-za-5-minut-i-ubrat/' => 'https://naturallift.store/kak-rasslabit-liczo-za-5-minut-i-ubrat/',
];

$fixed = 0;
$posts = get_posts([
    'post_type' => ['post', 'page'],
    'post_status' => 'any',
    'numberposts' => -1,
]);

foreach ($posts as $post) {
    $content = (string) $post->post_content;
    $updated = $content;
    foreach ($replacements as $from => $to) {
        $updated = str_replace($from, $to, $updated);
    }
    if ($updated !== $content) {
        wp_update_post([
            'ID' => (int) $post->ID,
            'post_content' => $updated,
        ]);
        echo 'OK fixed post=' . (int) $post->ID . ' slug=' . $post->post_name . PHP_EOL;
        $fixed++;
    }
}

echo 'total_fixed=' . $fixed . PHP_EOL;
"""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = load_env(root)
    public = env.get("PUBLIC_SITE_URL") or env.get("WP_SITE_URL") or ""
    if not public:
        print("PUBLIC_SITE_URL missing", file=sys.stderr)
        return 2
    out = publish_via_ftp(env, PHP, public)
    print(out)
    return 0 if "total_fixed=" in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
