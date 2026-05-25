from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models import Order, User

kitchen_bp = Blueprint("kitchen", __name__)


def kitchen_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_role") not in ("kitchen", "admin"):
            return redirect(url_for("kitchen.login"))
        return view(*args, **kwargs)

    return wrapped


@kitchen_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_role") in ("kitchen", "admin"):
        return redirect(url_for("kitchen.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username, role="kitchen").first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_role"] = user.role
            session["username"] = user.username
            session.modified = True
            return redirect(url_for("kitchen.dashboard"))
        flash("Invalid kitchen username or password.")
    return render_template("kitchen/login.html")


@kitchen_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("kitchen.login"))


@kitchen_bp.route("/")
@kitchen_required
def dashboard():
    pending_orders = Order.query.filter_by(status="Pending").order_by(Order.order_date.desc()).all()
    preparing_orders = Order.query.filter_by(status="Preparing").order_by(Order.order_date.desc()).all()
    completed_orders = Order.query.filter_by(status="Completed").order_by(Order.order_date.desc()).limit(40).all()
    return render_template(
        "kitchen/dashboard.html",
        pending_orders=pending_orders,
        preparing_orders=preparing_orders,
        completed_orders=completed_orders,
    )


@kitchen_bp.route("/order/<int:order_id>/next-status", methods=["POST"])
@kitchen_required
def next_status(order_id: int):
    order = Order.query.get_or_404(order_id)
    if order.status == "Pending":
        order.status = "Preparing"
    elif order.status == "Preparing":
        order.status = "Completed"
    db.session.commit()
    flash(f"Order #{order.id} moved to {order.status}.")
    return redirect(url_for("kitchen.dashboard"))
