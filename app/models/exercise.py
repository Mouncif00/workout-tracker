from sqlalchemy import Column, Integer, String, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class ExerciseCategory(str, enum.Enum):
    STRENGTH = "strength"
    CARDIO = "cardio"
    FLEXIBILITY = "flexibility"
    BALANCE = "balance"
    PLYOMETRICS = "plyometrics"


class MuscleGroup(str, enum.Enum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    CORE = "core"
    LEGS = "legs"
    GLUTES = "glutes"
    FULL_BODY = "full_body"
    CARDIO = "cardio"


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)   # ExerciseCategory
    muscle_group = Column(String(50), nullable=False)  # MuscleGroup
    equipment = Column(String(100), nullable=True)  # e.g. "barbell", "dumbbell", "none"
    instructions = Column(Text, nullable=True)

    # Relationships
    workout_exercises = relationship("WorkoutExercise", back_populates="exercise")
