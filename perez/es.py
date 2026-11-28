from flask import Blueprint, render_template
from .about import about_context
from .projects import get_sorted_projects

bp = Blueprint("es", __name__, url_prefix="/es")

@bp.route('/', strict_slashes=False)
def index():
    return render_template("es/index.html")

@bp.route('/about', strict_slashes=False)
def about():
    return render_template("es/about.html", **about_context())

@bp.route('/resume', strict_slashes=False)
def resume():
    return render_template("es/resume.html")

@bp.route('/projects', strict_slashes=False)
def projects():
    return render_template("es/projects.html", projects=get_sorted_projects())

@bp.route('/contact', strict_slashes=False)
def contact():
    return render_template("es/contact.html")
