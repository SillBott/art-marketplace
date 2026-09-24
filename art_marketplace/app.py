import os
from flask import Flask, send_from_directory, render_template

from config import Config
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import bp as auth_bp
    from routes.gallery import bp as gallery_bp
    from routes.artist import bp as artist_bp
    from routes.cart import bp as cart_bp
    from routes.orders import bp as orders_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(artist_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    # Serve uploaded artwork/slip images. On Vercel these live under /tmp
    # and are NOT persistent across deployments/invocations — see README.
    @app.route("/uploads/<subdir>/<filename>")
    def uploaded_file(subdir, filename):
        folder = os.path.join(app.config["UPLOAD_FOLDER"], subdir)
        return send_from_directory(folder, filename)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="ไม่มีสิทธิ์เข้าถึงหน้านี้"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="ไม่พบหน้าที่ต้องการ"), 404

    @app.cli.command("init-db")
    def init_db():
        """flask --app app init-db"""
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db():
        """flask --app app seed-db"""
        from seed import run_seed
        run_seed()
        print("Database seeded with demo data.")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
