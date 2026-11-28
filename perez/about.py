from datetime import date

from flask import Blueprint, render_template
from .letterboxd import get_favorite_films
from .youtube_music import get_favorite_music

bp = Blueprint("about", __name__, url_prefix="/about")

# Start dates behind the "N years" on the about page, so it never goes stale.
ENGINEERING_START = date(2016, 2, 1)  # first DevOps role (Fenway Group)
BEEKEEPING_START = date(2016, 2, 1)   # bees and garden, same ten years


def years_since(start):
    """Returns how many whole years have passed since a date."""
    today = date.today()
    return today.year - start.year - ((today.month, today.day) < (start.month, start.day))


def about_context():
    """Everything the about page needs, shared by the English and German routes."""
    return {
        "films": get_favorite_films(),
        "tracks": get_favorite_music(),
        "engineering_years": years_since(ENGINEERING_START),
        "beekeeping_years": years_since(BEEKEEPING_START),
    }


@bp.route('/')
def about():
    return render_template("about.html", **about_context())
