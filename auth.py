from functools import wraps

from flask import redirect
from flask import request
from flask import session
from flask import url_for

from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from database import get_connection


def create_user(username, password, role="admin"):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO users (
            username,
            password_hash,
            role
        )
        VALUES (?, ?, ?)
        """,
        (
            username,
            generate_password_hash(password),
            role,
        ),
    )

    conn.commit()
    conn.close()


def authenticate(username, password):
    conn = get_connection()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        AND active = 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    if not user:
        return False

    return check_password_hash(
        user["password_hash"],
        password,
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped