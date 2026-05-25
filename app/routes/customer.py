from decimal import Decimal

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models import ItemMaster, Order, OrderDetail, RestaurantTable

customer_bp = Blueprint("customer", __name__)


def _round_money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))


def _wants_json() -> bool:
    if request.args.get("format") == "json":
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"], default="text/html")
    return best == "application/json"


def _cart() -> dict[str, int]:
    raw = session.get("cart") or {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        try:
            qty = int(value)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            out[str(key)] = qty
    return out


def _set_cart(cart: dict[str, int]) -> None:
    session["cart"] = cart
    session.modified = True


def _table_id() -> int | None:
    table_id = session.get("table_id")
    if table_id is None:
        return None
    try:
        return int(table_id)
    except (TypeError, ValueError):
        return None


def _has_active_order(table_id: int) -> bool:
    active = (
        Order.query.filter(Order.table_id == table_id, Order.status.in_(("Pending", "Preparing")))
        .order_by(Order.order_date.desc())
        .first()
    )
    return active is not None


@customer_bp.route("/")
def home():
    table_id = request.args.get("table_id", type=int)
    if table_id is not None:
        table = RestaurantTable.query.get(table_id)
        if table:
            session["table_id"] = table.id
            session.modified = True
            return redirect(url_for("customer.menu"))
        flash("Invalid table. Please scan a valid QR code.")
    return render_template("customer/home.html", table_id=_table_id())


@customer_bp.route("/menu", methods=["GET"])
def menu():
    table_id = _table_id()
    if table_id is None:
        flash("Scan the table QR code to start ordering.")
        return redirect(url_for("customer.home"))

    all_items = ItemMaster.query.order_by(ItemMaster.category_name, ItemMaster.item_name).all()
    grouped: dict[str, list[ItemMaster]] = {}
    for item in all_items:
        grouped.setdefault(item.category_name or "Others", []).append(item)

    if _wants_json():
        return jsonify(
            {
                "categories": [
                    {
                        "name": category_name,
                        "items": [
                            {"id": i.id, "name": i.item_name, "price": float(i.price), "image": i.image or ""}
                            for i in items
                        ],
                    }
                    for category_name, items in grouped.items()
                ]
            }
        )

    cart = _cart()
    return render_template(
        "customer/menu.html",
        grouped_items=grouped,
        table_id=table_id,
        cart_qty=sum(cart.values()) if cart else 0,
    )


@customer_bp.route("/cart", methods=["GET"])
def cart_page():
    table_id = _table_id()
    if table_id is None:
        flash("Scan the table QR code first.")
        return redirect(url_for("customer.home"))

    cart = _cart()
    item_ids = [int(i) for i in cart.keys()]
    items = ItemMaster.query.filter(ItemMaster.id.in_(item_ids)).all() if item_ids else []
    by_id = {item.id: item for item in items}

    lines = []
    grand_total = Decimal("0")
    for sid, qty in cart.items():
        item = by_id.get(int(sid))
        if not item or item.status != "Available":
            continue
        line_total = _round_money(Decimal(item.price) * qty)
        grand_total += line_total
        lines.append({"item": item, "quantity": qty, "line_total": line_total})

    return render_template(
        "customer/cart.html",
        lines=lines,
        grand_total=_round_money(grand_total),
        table_id=table_id,
    )


@customer_bp.route("/cart/add", methods=["POST"])
def cart_add():
    if _table_id() is None:
        return redirect(url_for("customer.home"))

    item_id = request.form.get("item_id", type=int)
    qty = request.form.get("quantity", default=1, type=int) or 1
    if not item_id or qty < 1:
        flash("Invalid item.")
        return redirect(url_for("customer.menu"))

    item = ItemMaster.query.get(item_id)
    if not item or item.status != "Available":
        flash("Item is not available.")
        return redirect(url_for("customer.menu"))

    cart = _cart()
    key = str(item_id)
    cart[key] = cart.get(key, 0) + qty
    _set_cart(cart)
    flash(f"Added {item.item_name} to cart.")
    return redirect(url_for("customer.menu"))


@customer_bp.route("/cart/update", methods=["POST"])
def cart_update():
    if _table_id() is None:
        return redirect(url_for("customer.home"))

    cart = _cart()
    for key in list(cart.keys()):
        field = f"qty_{key}"
        if field in request.form:
            qty = request.form.get(field, type=int)
            if qty is None or qty < 1:
                cart.pop(key, None)
            else:
                cart[key] = qty
    _set_cart(cart)
    flash("Cart updated.")
    return redirect(url_for("customer.cart_page"))


@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
def cart_remove(item_id: int):
    cart = _cart()
    cart.pop(str(item_id), None)
    _set_cart(cart)
    flash("Item removed.")
    return redirect(url_for("customer.cart_page"))


def _create_order(table_id: int, payload: list[dict]) -> Order:
    if not payload:
        raise ValueError("No items in order.")

    table = RestaurantTable.query.get(table_id)
    if not table:
        raise ValueError("Invalid table.")
    if _has_active_order(table_id):
        raise ValueError("Previous order is active for this table. Please wait.")

    total = Decimal("0")
    lines: list[tuple[ItemMaster, int, Decimal]] = []
    for row in payload:
        item = ItemMaster.query.get(int(row["item_id"]))
        qty = int(row["quantity"])
        if not item or item.status != "Available" or qty < 1:
            continue
        unit_price = Decimal(item.price)
        total += _round_money(unit_price * qty)
        lines.append((item, qty, unit_price))

    if not lines:
        raise ValueError("No valid items to order.")

    order = Order(table_id=table_id, total_amount=_round_money(total), status="Pending")
    db.session.add(order)
    db.session.flush()
    for item, qty, unit_price in lines:
        db.session.add(OrderDetail(order_id=order.id, item_id=item.id, quantity=qty, price=unit_price))
    db.session.commit()
    return order


@customer_bp.route("/checkout", methods=["POST"])
def checkout():
    table_id = _table_id()
    if table_id is None:
        flash("Session expired. Scan QR again.")
        return redirect(url_for("customer.home"))

    cart = _cart()
    payload = [{"item_id": int(item_id), "quantity": qty} for item_id, qty in cart.items()]
    try:
        order = _create_order(table_id, payload)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("customer.cart_page"))

    _set_cart({})
    return redirect(url_for("customer.order_success", order_id=order.id))


@customer_bp.route("/order/success/<int:order_id>")
def order_success(order_id: int):
    order = Order.query.get_or_404(order_id)
    current_table = _table_id()
    if current_table is not None and order.table_id != current_table:
        flash("Order not found for this table.")
        return redirect(url_for("customer.home"))

    return render_template("customer/order_success.html", order=order)


@customer_bp.route("/order/status/<int:order_id>")
def order_status(order_id: int):
    order = Order.query.get_or_404(order_id)
    if _wants_json():
        return jsonify({"order_id": order.id, "status": order.status, "total_amount": float(order.total_amount)})
    return render_template("customer/order_status.html", order=order)
