"""Populate the database with demo accounts and categories so the app is
usable immediately after `flask --app app init-db && flask --app app seed-db`.

Demo logins (all passwords: password123):
  admin / admin@example.com      (role: admin)
  staff1 / staff1@example.com    (role: staff)
  artist1 / artist1@example.com  (role: customer + artist profile)
  buyer1 / buyer1@example.com    (role: customer)
"""
from extensions import db
from models import User, ArtistProfile, Category


def run_seed():
    if User.query.filter_by(username="admin").first():
        print("Demo data already present, skipping.")
        return

    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("password123")

    staff = User(username="staff1", email="staff1@example.com", role="staff")
    staff.set_password("password123")

    artist_user = User(username="artist1", email="artist1@example.com", role="customer")
    artist_user.set_password("password123")

    buyer = User(username="buyer1", email="buyer1@example.com", role="customer")
    buyer.set_password("password123")

    db.session.add_all([admin, staff, artist_user, buyer])
    db.session.flush()

    profile = ArtistProfile(
        user_id=artist_user.id,
        display_name="Artist One",
        school="คณะศิลปกรรมศาสตร์",
        bio="นักศึกษาปี 3 ชอบวาดภาพสีน้ำและดิจิทัลอาร์ต",
        commission_rate=0.80,
    )
    db.session.add(profile)

    for name in ["ภาพวาดสีน้ำ", "ดิจิทัลอาร์ต", "ภาพร่างดินสอ", "ภาพสีอะคริลิก"]:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))

    db.session.commit()
    print("Seeded: admin, staff1, artist1, buyer1 (password: password123)")
