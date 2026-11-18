from flask import Blueprint, render_template
from .letterboxd import get_favorite_films

bp = Blueprint("about", __name__, url_prefix="/about")

@bp.route('/')
def about():
    return render_template("about.html", films=get_favorite_films())
