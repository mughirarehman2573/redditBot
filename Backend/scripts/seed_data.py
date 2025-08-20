# backend/scripts/seed_data.py
from Backend.app.db.session import SessionLocal
from Backend.app.models.niche import Niche


def seed_niches():
    """Seed initial niches."""
    db = SessionLocal()
    try:
        niches = [
            {"name": "Technology", "description": "Tech news, programming, gadgets"},
            {"name": "Gaming", "description": "Video games, consoles, gaming news"},
            {"name": "Sports", "description": "Sports news, teams, athletes"},
            {"name": "Music", "description": "Music news, artists, albums"},
            {"name": "Movies", "description": "Movies, TV shows, entertainment"},
            {"name": "Science", "description": "Scientific discoveries, research"},
            {"name": "Programming", "description": "Coding, software development"},
            {"name": "Crypto", "description": "Cryptocurrency, blockchain, NFTs"},
            {"name": "Fitness", "description": "Exercise, health, nutrition"},
            {"name": "Travel", "description": "Travel tips, destinations, photos"}
        ]

        for niche_data in niches:
            if not db.query(Niche).filter(Niche.name == niche_data["name"]).first():
                niche = Niche(**niche_data)
                db.add(niche)

        db.commit()
        print("✅ Niches seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding niches: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_niches()