import json
import os


def test_vercel_json_configuration():
    """Verify vercel.json rewrites and HTTP security headers conform to LIFELINK spec."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    vercel_path = os.path.join(project_root, "vercel.json")

    assert os.path.exists(vercel_path), f"vercel.json not found at {vercel_path}"

    with open(vercel_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Check rewrites
    rewrites = config.get("rewrites", [])
    api_rewrite = next((r for r in rewrites if r.get("source") == "/api/(.*)"), None)
    assert api_rewrite is not None, "Missing rewrite for /api/(.*)"
    assert api_rewrite.get("destination") == "api/index.py"

    spa_rewrite = next((r for r in rewrites if r.get("source") == "/(.*)"), None)
    assert spa_rewrite is not None, "Missing SPA fallback rewrite for /(.*)"
    assert spa_rewrite.get("destination") == "/apps/web/dist/$1"

    # Check security headers
    headers_config = config.get("headers", [])
    assert len(headers_config) > 0, "No headers configured in vercel.json"

    global_headers = headers_config[0].get("headers", [])
    header_map = {h["key"].lower(): h["value"] for h in global_headers}

    assert header_map.get("x-frame-options") == "DENY", "X-Frame-Options must be DENY (T-00-03)"
    assert header_map.get("x-content-type-options") == "nosniff", "X-Content-Type-Options must be nosniff (T-00-04)"
    assert header_map.get("referrer-policy") == "no-referrer"
    assert "content-security-policy" in header_map
    assert "permissions-policy" in header_map
