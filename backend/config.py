from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MODEL_NAME: str = "yolo26n.pt"
    CONFIDENCE_THRESHOLD: float = 0.3
    SKIP_FRAMES: int = 3
    MAX_TRACK_DISTANCE: int = 80
    TRAJECTORY_LENGTH: int = 60
    PROXIMITY_THRESHOLD: float = 100.0
    LOITER_SECONDS: float = 8.0
    LOITER_COOLDOWN: float = 30.0
    NEAR_MISS_COOLDOWN: float = 5.0
    FALLEN_FRAME_COUNT: int = 5
    HARDHAT_COLOR_THRESHOLD: float = 0.15
    STREAM_FPS: int = 10
    UPLOAD_DIR: str = "uploads"
    DB_PATH: str = "hazardlens.db"
    DEMO_FRAME_COUNT: int = 500
    DEMO_FPS: int = 10

    class Config:
        env_prefix = "HL_"


settings = Settings()
