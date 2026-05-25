"""
Seed the exercises table with a comprehensive exercise library.
Run: python scripts/seed_exercises.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal, engine
from app.core.database import Base
import app.models  # ensure all models are registered
from app.models.exercise import Exercise

EXERCISES = [
    # ── STRENGTH / CHEST ──────────────────────────────────────────
    {"name": "Barbell Bench Press", "category": "strength", "muscle_group": "chest",
     "equipment": "barbell", "description": "Classic compound chest press on a flat bench.",
     "instructions": "Lie flat, grip bar slightly wider than shoulder width, lower to chest and press up."},
    {"name": "Incline Dumbbell Press", "category": "strength", "muscle_group": "chest",
     "equipment": "dumbbell", "description": "Upper-chest focused press on inclined bench.",
     "instructions": "Set bench to 30–45°, press dumbbells from shoulder height to full extension."},
    {"name": "Cable Fly", "category": "strength", "muscle_group": "chest",
     "equipment": "cable", "description": "Isolation movement for chest stretch and squeeze.",
     "instructions": "Stand between cables, bring handles together in an arc at chest height."},
    {"name": "Push-Up", "category": "strength", "muscle_group": "chest",
     "equipment": "none", "description": "Bodyweight pressing movement.",
     "instructions": "Start in plank position, lower chest to floor then push back up."},

    # ── STRENGTH / BACK ───────────────────────────────────────────
    {"name": "Barbell Deadlift", "category": "strength", "muscle_group": "back",
     "equipment": "barbell", "description": "King of all compound lifts, targets posterior chain.",
     "instructions": "Hinge at hip, grip bar, maintain neutral spine, drive hips forward to stand."},
    {"name": "Pull-Up", "category": "strength", "muscle_group": "back",
     "equipment": "pull-up bar", "description": "Bodyweight vertical pull.",
     "instructions": "Hang from bar, pull chest to bar, lower with control."},
    {"name": "Bent-Over Row", "category": "strength", "muscle_group": "back",
     "equipment": "barbell", "description": "Horizontal pull for lat and upper back thickness.",
     "instructions": "Hinge to 45°, pull bar to lower chest, retract shoulder blades."},
    {"name": "Lat Pulldown", "category": "strength", "muscle_group": "back",
     "equipment": "cable", "description": "Machine-assisted vertical pull.",
     "instructions": "Grip bar wide, pull to upper chest, focus on lat contraction."},
    {"name": "Seated Cable Row", "category": "strength", "muscle_group": "back",
     "equipment": "cable", "description": "Horizontal pull targeting mid-back.",
     "instructions": "Sit upright, pull handle to abdomen, squeeze shoulder blades."},

    # ── STRENGTH / SHOULDERS ──────────────────────────────────────
    {"name": "Overhead Press", "category": "strength", "muscle_group": "shoulders",
     "equipment": "barbell", "description": "Compound shoulder press.",
     "instructions": "Press barbell from chin to overhead, fully lock out arms."},
    {"name": "Dumbbell Lateral Raise", "category": "strength", "muscle_group": "shoulders",
     "equipment": "dumbbell", "description": "Isolation for medial deltoid.",
     "instructions": "Raise dumbbells out to sides to shoulder height with slight elbow bend."},
    {"name": "Face Pull", "category": "strength", "muscle_group": "shoulders",
     "equipment": "cable", "description": "Rear delt and external rotation health exercise.",
     "instructions": "Pull rope to face height, flare elbows wide, retract scapula."},

    # ── STRENGTH / ARMS ───────────────────────────────────────────
    {"name": "Barbell Curl", "category": "strength", "muscle_group": "arms",
     "equipment": "barbell", "description": "Primary bicep builder.",
     "instructions": "Curl bar from full extension to full contraction, control the negative."},
    {"name": "Hammer Curl", "category": "strength", "muscle_group": "arms",
     "equipment": "dumbbell", "description": "Targets brachialis and forearm.",
     "instructions": "Curl with neutral grip (thumbs up) to shoulder height."},
    {"name": "Tricep Dip", "category": "strength", "muscle_group": "arms",
     "equipment": "dip bar", "description": "Compound tricep exercise.",
     "instructions": "Lower body by bending elbows, press back to full extension."},
    {"name": "Skull Crusher", "category": "strength", "muscle_group": "arms",
     "equipment": "barbell", "description": "Isolation tricep movement on a bench.",
     "instructions": "Lower bar toward forehead by bending elbows, extend to start."},

    # ── STRENGTH / LEGS ───────────────────────────────────────────
    {"name": "Barbell Squat", "category": "strength", "muscle_group": "legs",
     "equipment": "barbell", "description": "Fundamental lower-body compound movement.",
     "instructions": "Bar on traps, squat to parallel or below, drive through heels to stand."},
    {"name": "Romanian Deadlift", "category": "strength", "muscle_group": "legs",
     "equipment": "barbell", "description": "Hamstring-dominant hip hinge.",
     "instructions": "Push hips back with soft knees, lower bar along shins, return by extending hips."},
    {"name": "Leg Press", "category": "strength", "muscle_group": "legs",
     "equipment": "machine", "description": "Machine-based quad-dominant press.",
     "instructions": "Place feet shoulder width on platform, press to full extension without locking knees."},
    {"name": "Walking Lunge", "category": "strength", "muscle_group": "legs",
     "equipment": "dumbbell", "description": "Unilateral leg exercise improving balance.",
     "instructions": "Step forward, lower back knee toward floor, alternate legs walking."},
    {"name": "Leg Curl", "category": "strength", "muscle_group": "legs",
     "equipment": "machine", "description": "Isolated hamstring curl.",
     "instructions": "Curl pad toward glutes, squeeze at top, lower with control."},
    {"name": "Calf Raise", "category": "strength", "muscle_group": "legs",
     "equipment": "machine", "description": "Gastrocnemius isolation.",
     "instructions": "Rise onto toes, pause at top, lower heel below platform for full stretch."},

    # ── STRENGTH / GLUTES ─────────────────────────────────────────
    {"name": "Hip Thrust", "category": "strength", "muscle_group": "glutes",
     "equipment": "barbell", "description": "Best glute activation exercise.",
     "instructions": "Shoulders on bench, bar on hips, drive hips to full extension, squeeze glutes."},
    {"name": "Glute Bridge", "category": "strength", "muscle_group": "glutes",
     "equipment": "none", "description": "Bodyweight glute isolation.",
     "instructions": "Lie on floor, feet flat, drive hips up and squeeze glutes at top."},
    {"name": "Cable Kickback", "category": "strength", "muscle_group": "glutes",
     "equipment": "cable", "description": "Isolation for glute-hamstring tie-in.",
     "instructions": "Attach ankle strap, kick leg back and up, focus on glute contraction."},

    # ── STRENGTH / CORE ───────────────────────────────────────────
    {"name": "Plank", "category": "strength", "muscle_group": "core",
     "equipment": "none", "description": "Isometric core stability exercise.",
     "instructions": "Hold push-up position on forearms, keep body rigid from head to heels."},
    {"name": "Cable Crunch", "category": "strength", "muscle_group": "core",
     "equipment": "cable", "description": "Weighted abdominal crunch.",
     "instructions": "Kneel, pull rope to knees while crunching abs, control the eccentric."},
    {"name": "Hanging Leg Raise", "category": "strength", "muscle_group": "core",
     "equipment": "pull-up bar", "description": "Advanced lower ab and hip flexor movement.",
     "instructions": "Hang from bar, raise legs to 90° or higher, lower with control."},
    {"name": "Russian Twist", "category": "strength", "muscle_group": "core",
     "equipment": "none", "description": "Rotational core movement.",
     "instructions": "Sit at 45°, feet off floor, rotate torso side to side."},

    # ── CARDIO ────────────────────────────────────────────────────
    {"name": "Treadmill Run", "category": "cardio", "muscle_group": "cardio",
     "equipment": "treadmill", "description": "Steady-state or interval running.",
     "instructions": "Set speed, maintain upright posture, land midfoot."},
    {"name": "Rowing Machine", "category": "cardio", "muscle_group": "full_body",
     "equipment": "rowing machine", "description": "Full-body low-impact cardio.",
     "instructions": "Drive with legs first, then lean back, then pull handle to chest."},
    {"name": "Jump Rope", "category": "cardio", "muscle_group": "cardio",
     "equipment": "jump rope", "description": "High-intensity cardio and coordination.",
     "instructions": "Jump on balls of feet, keep elbows close, small wrist rotations."},
    {"name": "Cycling", "category": "cardio", "muscle_group": "legs",
     "equipment": "bike", "description": "Low-impact cardiovascular exercise.",
     "instructions": "Adjust seat height, maintain cadence, keep back straight."},
    {"name": "Stair Climber", "category": "cardio", "muscle_group": "legs",
     "equipment": "stair climber", "description": "Glute and cardio focused machine.",
     "instructions": "Set pace, step fully onto each step, avoid leaning on rails."},

    # ── FULL BODY ─────────────────────────────────────────────────
    {"name": "Burpee", "category": "plyometrics", "muscle_group": "full_body",
     "equipment": "none", "description": "High-intensity full-body conditioning movement.",
     "instructions": "From standing: squat, jump feet back to plank, push-up, jump feet forward, jump up."},
    {"name": "Kettlebell Swing", "category": "strength", "muscle_group": "full_body",
     "equipment": "kettlebell", "description": "Hip-hinge power movement.",
     "instructions": "Hike kettlebell back between legs, drive hips forward to swing to shoulder height."},
    {"name": "Clean and Press", "category": "strength", "muscle_group": "full_body",
     "equipment": "barbell", "description": "Olympic-style full-body power movement.",
     "instructions": "Pull bar from floor to shoulders (clean), then press overhead."},

    # ── FLEXIBILITY ───────────────────────────────────────────────
    {"name": "Hip Flexor Stretch", "category": "flexibility", "muscle_group": "legs",
     "equipment": "none", "description": "Essential stretch for desk workers and athletes.",
     "instructions": "Kneel on one knee, push hips forward until you feel stretch in front of hip."},
    {"name": "Seated Hamstring Stretch", "category": "flexibility", "muscle_group": "legs",
     "equipment": "none", "description": "Static hamstring stretch.",
     "instructions": "Sit with legs extended, reach toward toes, hold position."},
    {"name": "Cat-Cow Stretch", "category": "flexibility", "muscle_group": "back",
     "equipment": "none", "description": "Spinal mobility and warm-up.",
     "instructions": "On all fours, alternate between arching back (cat) and dropping belly (cow)."},
    {"name": "Shoulder Cross-Body Stretch", "category": "flexibility", "muscle_group": "shoulders",
     "equipment": "none", "description": "Posterior shoulder stretch.",
     "instructions": "Pull one arm across body at shoulder height, hold 30 seconds each side."},
    {"name": "Foam Roll Thoracic Spine", "category": "flexibility", "muscle_group": "back",
     "equipment": "foam roller", "description": "Thoracic extension and mobility work.",
     "instructions": "Place roller under mid-back, support head, extend over roller."},
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_count = db.query(Exercise).count()
        if existing_count > 0:
            print(f"Exercises already seeded ({existing_count} records). Skipping.")
            return

        for ex_data in EXERCISES:
            ex = Exercise(**ex_data)
            db.add(ex)

        db.commit()
        print(f"✅ Seeded {len(EXERCISES)} exercises successfully.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
