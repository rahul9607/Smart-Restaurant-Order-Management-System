"""Initial users, tables, and menu items (idempotent)."""

from app.extensions import db
from app.models import ItemMaster, RestaurantTable, User


def ensure_seed_data() -> None:
    if User.query.filter_by(username="admin").first() is None:
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if User.query.filter_by(username="kitchen").first() is None:
        kitchen = User(username="kitchen", role="kitchen")
        kitchen.set_password("kitchen123")
        db.session.add(kitchen)

    if ItemMaster.query.count() == 0:
        items = [
            ItemMaster(
                item_name="Spring Rolls",
                category_name="Starters",
                price=120,
                image="",
                description="Crispy mixed vegetable spring rolls.",
                status="Available",
            ),
            ItemMaster(
                item_name="Tomato Soup",
                category_name="Starters",
                price=90,
                image="",
                description="Fresh tomato soup with mild herbs.",
                status="Available",
            ),
            ItemMaster(
                item_name="Paneer Tikka",
                category_name="Main Course",
                price=220,
                image="",
                description="Grilled paneer cubes with Indian spices.",
                status="Available",
            ),
            ItemMaster(
                item_name="Veg Biryani",
                category_name="Main Course",
                price=180,
                image="",
                description="Fragrant rice with vegetables and spices.",
                status="Available",
            ),
            ItemMaster(
                item_name="Masala Chai",
                category_name="Beverages",
                price=40,
                image="",
                description="Classic Indian tea.",
                status="Available",
            ),
            ItemMaster(
                item_name="Cold Coffee",
                category_name="Beverages",
                price=80,
                image="",
                description="Chilled coffee with cream.",
                status="Available",
            ),
            ItemMaster(
                item_name="Ice Cream",
                category_name="Desserts",
                price=100,
                image="",
                description="Seasonal flavored ice cream scoop.",
                status="Available",
            ),
        ]
        db.session.add_all(items)

    if RestaurantTable.query.count() == 0:
        for n in range(1, 9):
            t = RestaurantTable(
                table_number=str(n),
                qr_code=f"/?table_id={n}",
                status="available",
            )
            db.session.add(t)

    db.session.commit()
