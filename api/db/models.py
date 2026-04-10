from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime ,timezone
from db.base import Base

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name          = Column(String(100))

    cameras = relationship("Camera", back_populates="user")
    alerts  = relationship("Alert", back_populates="user")


class Camera(Base):
    __tablename__ = "cameras"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name       = Column(String(100), nullable=False)
    stream_url = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True)

    user             = relationship("User", back_populates="cameras")
    danger_zones     = relationship("DangerZone", back_populates="camera")
    detection_events = relationship("DetectionEvent", back_populates="camera")


class DangerZone(Base):
    __tablename__ = "danger_zones"

    id          = Column(Integer, primary_key=True)
    camera_id   = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"))
    label       = Column(String(100))
    zone_points = Column(JSONB, nullable=False)

    camera = relationship("Camera", back_populates="danger_zones")


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id            = Column(Integer, primary_key=True)
    camera_id     = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"))
    event_type    = Column(String(50), nullable=False)
    confidence    = Column(Float)
    bbox          = Column(JSONB)
    snapshot_path = Column(String(255))
    detected_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    camera = relationship("Camera", back_populates="detection_events")
    alerts = relationship("Alert", back_populates="detection_event")


class Alert(Base):
    __tablename__ = "alerts"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    detection_id = Column(Integer, ForeignKey("detection_events.id", ondelete="SET NULL"), nullable=True)
    message      = Column(Text)
    is_read      = Column(Boolean, default=False)
    sent_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user            = relationship("User", back_populates="alerts")
    detection_event = relationship("DetectionEvent", back_populates="alerts")
