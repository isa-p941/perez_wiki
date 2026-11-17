from flask import Blueprint, render_template
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

bp = Blueprint("projects", __name__, url_prefix="/projects")

PROJECTS = [
    {
        "repo": "perez_wiki",
        "url": "https://github.com/isa-p941/perez_wiki",
        "icon": "img/favicon.ico",
        "name": "perez.wiki",
        "desc_en": "this website! a basic website built on Flask and deployed with GitHub Actions.",
        "desc_de": "diese Website! eine einfache Website, erstellt mit Flask und über GitHub Actions bereitgestellt.",
    },
    {
        "repo": "infra_perez_wiki",
        "url": "https://github.com/isa-p941/infra_perez_wiki",
        "icon": "img/terraform.png",
        "name": "infra_perez_wiki",
        "desc_en": "a cloud infrastructure demonstration that can deploy this website. Deploys Jenkins to an AWS cluster, and deploys Grafana to an Azure cluster, and sets up a deployment pipeline for this website. Demos available upon request.",
        "desc_de": "eine Cloud-Infrastruktur-Demonstration, die diese Website bereitstellen kann. Stellt Jenkins auf einem AWS-Cluster und Grafana auf einem Azure-Cluster bereit und richtet eine Deployment-Pipeline für diese Website ein. Demos auf Anfrage verfügbar.",
    },
    {
        "repo": "find_a_flood",
        "url": "https://github.com/isa-p941/find_a_flood",
        "icon": "img/findaflood.png",
        "name": "find_a_flood",
        "desc_en": "a Python CLI that finds potentially flooding rivers near you with NOAA river-gauge data",
        "desc_de": "ein Python-CLI-Tool, das potenziell überflutende Flüsse in deiner Nähe mit NOAA-Pegeldaten findet",
    },
    {
        "repo": "Parallel-Image-Processing",
        "url": "https://github.com/isa-p941/Parallel-Image-Processing",
        "icon": "img/tensorflow.png",
        "name": "BCIC",
        "desc_en": "a distributed TensorFlow-based Image Processor",
        "desc_de": "ein verteilter TensorFlow-basierter Bildprozessor",
    },
    {
        "repo": "CyberVision",
        "url": "https://github.com/isa-p941/CyberVision",
        "icon": "img/matlab.png",
        "name": "CyberVision",
        "desc_en": "a MatLab/Python Image Blender and Motion Detector",
        "desc_de": "ein MatLab/Python Bildmischer und Bewegungsmelder",
    },
]

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600


def _fetch_last_commit(repo):
    url = f"https://api.github.com/repos/isa-p941/{repo}/commits?per_page=1"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data[0]["commit"]["committer"]["date"]
    except Exception:
        return "1970-01-01T00:00:00Z"


def get_sorted_projects():
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    def _enrich(p):
        raw = _fetch_last_commit(p["repo"])
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            display = dt.strftime("%-d %b %Y")
        except Exception:
            display = ""
        return {**p, "last_commit": raw, "last_commit_display": display}

    projects = [_enrich(p) for p in PROJECTS]
    projects.sort(key=lambda p: p["last_commit"], reverse=True)
    _cache["data"] = projects
    _cache["ts"] = now
    return projects


@bp.route('/')
def projects():
    return render_template("projects.html", projects=get_sorted_projects())
