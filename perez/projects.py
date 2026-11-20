"""Tends the projects page: what I have built, and how each hive is doing.

Each project is checked against GitHub for its latest commit and the state of
its latest build, then the whole lot is sorted with the most recently tended
at the top. The results are kept in a jar for an hour so visitors do not have
to wait on GitHub.
"""

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
    """Builds the address of a repository's page on GitHub.

    Args:
        repo: The repository's name, such as "perez_wiki".

    Returns:
        The full URL of the repository.
    """
    return f"{_GITHUB_URL}/{_GITHUB_USER}/{repo}"


def _repo_api_url(repo, path):
    """Builds the address of one of a repository's GitHub API endpoints.

    Args:
        repo: The repository's name, such as "perez_wiki".
        path: The endpoint to visit, with any query string, such as
            "commits?per_page=1".

    Returns:
        The full API URL.
    """
    return f"{_GITHUB_API}/repos/{_GITHUB_USER}/{repo}/{path}"


def _gh_get(url):
    """Asks the GitHub API a question and returns its answer.

    If a GITHUB_TOKEN is set in the environment it is shown at the door,
    which earns a much higher rate limit than anonymous visitors get.

    Args:
        url: The API address to visit.

    Returns:
        The decoded JSON response.

    Raises:
        urllib.error.URLError: If GitHub is unreachable, refuses us, or takes
            longer than five seconds to answer.
    """
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _fetch_last_commit(repo):
    """Finds out when a repository was last touched.

    Args:
        repo: The repository's name.

    Returns:
        The latest commit's timestamp as an ISO 8601 string. If GitHub cannot
        say, the start of 1970 is returned, which sinks the project to the
        bottom of the list rather than breaking the page.
    """
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
    """Checks how the latest GitHub Actions run went.

    Args:
        repo: The repository's name.

    Returns:
        A tuple of (status, url). The status is "passing", "failed",
        "building" or "unknown", and the url points to the run's logs, or is
        None when there is no run to point to. Any trouble talking to GitHub
        counts as "unknown".
    """
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
    """Returns every project, freshest first, with its GitHub details attached.

    All the projects are visited at once rather than one after another, so
    the wait is only as long as the slowest reply. The result is kept for an
    hour, and a visitor who arrives while the jar is full gets it at once.

    Returns:
        A list of project dicts sorted by last commit, newest first. Each has
        everything in PROJECTS plus a "url", "last_commit",
        "last_commit_display", "build_status", "build_color" and "build_url".
    """
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    def _enrich(p):
        """Adds a project's repository link, last commit and build status."""
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
    """Serves the English projects page."""
    return render_template("projects.html", projects=get_sorted_projects())
