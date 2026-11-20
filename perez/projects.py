from flask import Blueprint, render_template
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

bp = Blueprint("projects", __name__, url_prefix="/projects")

PROJECTS = [
    {
        "repo": "perez_wiki",
        "icon": "img/favicon.ico",
        "name": "perez.wiki",
        "desc_en": "this website! a basic website built on Flask and deployed with GitHub Actions.",
        "desc_de": "diese Website! eine einfache Website, erstellt mit Flask und über GitHub Actions bereitgestellt.",
    },
    {
        "repo": "infra_perez_wiki",
        "icon": "img/terraform.png",
        "name": "infra_perez_wiki",
        "desc_en": "a cloud infrastructure demonstration that can deploy this website. Deploys Jenkins to an AWS cluster, and deploys Grafana to an Azure cluster, and sets up a deployment pipeline for this website. Demos available upon request.",
        "desc_de": "eine Cloud-Infrastruktur-Demonstration, die diese Website bereitstellen kann. Stellt Jenkins auf einem AWS-Cluster und Grafana auf einem Azure-Cluster bereit und richtet eine Deployment-Pipeline für diese Website ein. Demos auf Anfrage verfügbar.",
    },
    {
        "repo": "find_a_flood",
        "icon": "img/findaflood.png",
        "name": "find_a_flood",
        "desc_en": "a Python CLI that finds potentially flooding rivers near you with NOAA river-gauge data",
        "desc_de": "ein Python-CLI-Tool, das potenziell überflutende Flüsse in deiner Nähe mit NOAA-Pegeldaten findet",
    },
    {
        "repo": "Parallel-Image-Processing",
        "icon": "img/tensorflow.png",
        "name": "BCIC",
        "desc_en": "a distributed TensorFlow-based Image Processor",
        "desc_de": "ein verteilter TensorFlow-basierter Bildprozessor",
    },
    {
        "repo": "CyberVision",
        "icon": "img/matlab.png",
        "name": "CyberVision",
        "desc_en": "a MatLab/Python Image Blender and Motion Detector",
        "desc_de": "ein MatLab/Python Bildmischer und Bewegungsmelder",
    },
]

_GITHUB_USER = "isa-p941"
_GITHUB_URL = "https://github.com"
_GITHUB_API = "https://api.github.com"

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600


def _repo_url(repo):
    return f"{_GITHUB_URL}/{_GITHUB_USER}/{repo}"


def _repo_api_url(repo, path):
    return f"{_GITHUB_API}/repos/{_GITHUB_USER}/{repo}/{path}"


def _gh_get(url):
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _fetch_last_commit(repo):
    try:
        data = _gh_get(_repo_api_url(repo, "commits?per_page=1"))
        return data[0]["commit"]["committer"]["date"]
    except Exception:
        return "1970-01-01T00:00:00Z"


_BUILD_COLORS = {
    "passing":  "#3a3",
    "failed":   "#c33",
    "building": "#e82",
    "unknown":  "#888",
}

def _fetch_build_status(repo):
    try:
        data = _gh_get(_repo_api_url(repo, "actions/runs?per_page=1"))
        runs = data.get("workflow_runs", [])
        if not runs:
            return "unknown", None
        run = runs[0]
        url = run.get("html_url")
        if run.get("status") in ("queued", "in_progress"):
            return "building", url
        conclusion = run.get("conclusion")
        if conclusion == "success":
            return "passing", url
        if conclusion in ("failure", "timed_out", "action_required"):
            return "failed", url
        return "unknown", url
    except Exception:
        return "unknown", None


def get_sorted_projects():
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    def _enrich(p):
        raw = _fetch_last_commit(p["repo"])
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            commit_display = dt.strftime("%-d %b %Y")
        except Exception:
            commit_display = ""
        build, build_url = _fetch_build_status(p["repo"])
        return {
            **p,
            "url": _repo_url(p["repo"]),
            "last_commit": raw,
            "last_commit_display": commit_display,
            "build_status": build,
            "build_color": _BUILD_COLORS[build],
            "build_url": build_url,
        }

    with ThreadPoolExecutor(max_workers=len(PROJECTS)) as pool:
        futures = {pool.submit(_enrich, p): p for p in PROJECTS}
        projects = [f.result() for f in as_completed(futures)]
    projects.sort(key=lambda p: p["last_commit"], reverse=True)
    _cache["data"] = projects
    _cache["ts"] = now
    return projects


@bp.route('/')
def projects():
    return render_template("projects.html", projects=get_sorted_projects())
