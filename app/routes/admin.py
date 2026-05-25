from datetime import datetime
from decimal import Decimal
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from app.extensions import db
from app.models import ItemMaster, Order, RestaurantTable, User

admin_bp = Blueprint("admin", __name__)


def _wants_json() -> bool:
    if request.args.get("format") == "json":
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"], default="text/html")
    return best == "application/json"


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_role") != "admin":
            if _wants_json():
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/")
def admin_home():
    if session.get("user_role") == "admin":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_role") == "admin":
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username, role="admin").first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_role"] = user.role
            session["username"] = user.username
            session.modified = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin username or password.")
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    pending = Order.query.filter_by(status="Pending").count()
    preparing = Order.query.filter_by(status="Preparing").count()
    completed = Order.query.filter_by(status="Completed").count()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = Order.query.filter(Order.status == "Completed", Order.order_date >= today_start).count()
    return render_template(
        "admin/dashboard.html",
        pending=pending,
        preparing=preparing,
        completed=completed,
        completed_today=completed_today,
        item_count=ItemMaster.query.count(),
        table_count=RestaurantTable.query.count(),
        kitchen_user_count=User.query.filter_by(role="kitchen").count(),
    )


@admin_bp.route("/menu", methods=["GET", "POST"])
@admin_required
def menu_list():
    if request.method == "POST":
        item_name = (request.form.get("item_name") or "").strip()
        category_name = (request.form.get("category_name") or "").strip()
        description = (request.form.get("description") or "").strip()
        image = (request.form.get("image") or "").strip()
        status = request.form.get("status") or "Available"  # Available, Out of Stock
        try:
            price = Decimal(str(request.form.get("price")))
        except Exception:
            flash("Invalid price.")
            return redirect(url_for("admin.menu_list"))

        if status not in ("Available", "Out of Stock"):
            flash("Invalid item status.")
            return redirect(url_for("admin.menu_list"))

        if not item_name or not category_name:
            flash("Item name and category are required.")
            return redirect(url_for("admin.menu_list"))

        db.session.add(
            ItemMaster(
                item_name=item_name,
                category_name=category_name,
                price=price,
                image=image or None,
                description=description or None,
                status=status,
            )
        )
        db.session.commit()
        flash("Item added successfully.")
        return redirect(url_for("admin.menu_list"))

    items = ItemMaster.query.order_by(ItemMaster.category_name, ItemMaster.item_name).all()
    categories = db.session.query(ItemMaster.category_name).distinct().order_by(ItemMaster.category_name).all()
    return render_template("admin/menu_list.html", items=items, categories=[c[0] for c in categories if c[0]])


@admin_bp.route("/menu/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def menu_item_edit(item_id: int):
    item = ItemMaster.query.get_or_404(item_id)
    if request.method == "POST":
        item_name = (request.form.get("item_name") or "").strip()
        category_name = (request.form.get("category_name") or "").strip()
        description = (request.form.get("description") or "").strip()
        image = (request.form.get("image") or "").strip()
        status = request.form.get("status") or "Available"
        try:
            price = Decimal(str(request.form.get("price")))
        except Exception:
            flash("Invalid price.")
            return redirect(url_for("admin.menu_item_edit", item_id=item.id))

        if status not in ("Available", "Out of Stock"):
            flash("Invalid item status.")
            return redirect(url_for("admin.menu_item_edit", item_id=item.id))

        if not item_name or not category_name:
            flash("Item name and category are required.")
            return redirect(url_for("admin.menu_item_edit", item_id=item.id))

        item.item_name = item_name
        item.category_name = category_name
        item.price = price
        item.image = image or None
        item.description = description or None
        item.status = status
        db.session.commit()
        flash("Item updated successfully.")
        return redirect(url_for("admin.menu_list"))

    categories = db.session.query(ItemMaster.category_name).distinct().order_by(ItemMaster.category_name).all()
    return render_template("admin/menu_edit.html", item=item, categories=[c[0] for c in categories if c[0]])


@admin_bp.route("/menu/<int:item_id>/delete", methods=["POST"])
@admin_required
def menu_item_delete_form(item_id: int):
    item = ItemMaster.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.")
    return redirect(url_for("admin.menu_list"))


@admin_bp.route("/tables", methods=["GET", "POST"])
@admin_required
def tables():
    if request.method == "POST":
        table_number = (request.form.get("table_number") or "").strip()
        status = request.form.get("status") or "available"
        if not table_number:
            flash("Table number is required.")
            return redirect(url_for("admin.tables"))
        if RestaurantTable.query.filter_by(table_number=table_number).first():
            flash("Table number already exists.")
            return redirect(url_for("admin.tables"))
        db.session.add(RestaurantTable(table_number=table_number, qr_code=f"/?table_id={table_number}", status=status))
        db.session.commit()
        flash("Table added successfully.")
        return redirect(url_for("admin.tables"))

    all_tables = RestaurantTable.query.order_by(RestaurantTable.table_number).all()
    return render_template("admin/tables.html", tables=all_tables)


@admin_bp.route("/tables/<int:table_id>/delete", methods=["POST"])
@admin_required
def table_delete(table_id: int):
    table = RestaurantTable.query.get_or_404(table_id)
    db.session.delete(table)
    db.session.commit()
    flash("Table removed.")
    return redirect(url_for("admin.tables"))


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or "kitchen"
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("admin.users"))
        if role not in ("admin", "kitchen"):
            flash("Invalid role.")
            return redirect(url_for("admin.users"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("admin.users"))

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("User added successfully.")
        return redirect(url_for("admin.users"))

    app_users = User.query.order_by(User.role, User.username).all()
    return render_template("admin/users.html", users=app_users)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id: int):
    user = User.query.get_or_404(user_id)
    if user.username == "admin":
        flash("Default admin cannot be deleted.")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status") or "all"
    q = Order.query
    if status in ("Pending", "Preparing", "Completed"):
        q = q.filter_by(status=status)
    orders_list = q.order_by(Order.order_date.desc()).limit(200).all()
    return render_template("admin/orders.html", orders=orders_list, filter_status=status)


@admin_bp.route("/order/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id: int):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status") or ""
    if new_status not in ("Pending", "Preparing", "Completed"):
        flash("Invalid status.")
        return redirect(url_for("admin.orders"))
    order.status = new_status
    db.session.commit()
    flash("Order status updated.")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/reports")
@admin_required
def reports():
    rows = db.session.query(Order.status, func.count(Order.id), func.sum(Order.total_amount)).group_by(Order.status).all()
    summary = [{"status": r[0], "count": r[1], "total": float(r[2] or 0)} for r in rows]
    return render_template("admin/reports.html", summary=summary)

