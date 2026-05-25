from flask import Flask
from sqlalchemy import inspect, text

from app.extensions import db


def _ensure_schema_updates() -> None:
    """
    Small MySQL-safe schema updates for existing databases.
    SQLAlchemy's create_all() does not add missing columns.
    """
    inspector = inspect(db.engine)

    # orders.order_date (required by admin/kitchen ordering)
    if "orders" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("orders")}
        if "order_date" not in cols:
            # MySQL: add column with current timestamp default
            db.session.execute(
                text("ALTER TABLE orders ADD COLUMN order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
            )
            db.session.commit()

    # item_master.status legacy normalization (active/inactive -> Available/Out of Stock)
    if "item_master" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("item_master")}
        if "status" in cols:
            db.session.execute(text("UPDATE item_master SET status='Available' WHERE status='active' OR status='Active'"))
            db.session.execute(
                text(
                    "UPDATE item_master SET status='Out of Stock' WHERE status='inactive' OR status='Inactive' OR status='out_of_stock'"
                )
            )
            db.session.commit()


def create_app(config_object: str = "config.Config") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    db.init_app(app)

    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp
    from app.routes.kitchen import kitchen_bp

    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(kitchen_bp, url_prefix="/kitchen")

    with app.app_context():
        db.create_all()
        _ensure_schema_updates()
        from app import seed

        seed.ensure_seed_data()

    return app
