from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default="admin")  # admin, kitchen

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class ItemMaster(db.Model):
    __tablename__ = "item_master"

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(200), nullable=False, index=True)
    category_name = db.Column(db.String(120), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(512), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Available")  # Available, Out of Stock

    order_details = db.relationship("OrderDetail", back_populates="item", lazy=True)


class RestaurantTable(db.Model):
    __tablename__ = "restaurant_tables"

    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(32), nullable=False, unique=True)
    qr_code = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="available")

    orders = db.relationship("Order", back_populates="table", lazy=True)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("restaurant_tables.id"), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")  # Pending, Preparing, Completed
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    table = db.relationship("RestaurantTable", back_populates="orders")
    details = db.relationship(
        "OrderDetail",
        back_populates="order",
        lazy=True,
        cascade="all, delete-orphan",
    )


class OrderDetail(db.Model):
    __tablename__ = "order_details"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item_master.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="details")
    item = db.relationship("ItemMaster", back_populates="order_details")
