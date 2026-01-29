"""SQLAlchemy ORM models for MT5 Trading Dashboard."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String, primary_key=True)
    label = Column(String, nullable=True)
    history_start_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    info = relationship("AccountInfo", uselist=False, back_populates="account")
    credentials = relationship("AccountCredentials", uselist=False, back_populates="account")
    magics = relationship("Magic", back_populates="account")
    groups = relationship("MagicGroup", back_populates="account")
    deals = relationship("Deal", back_populates="account")
    positions = relationship("Position", back_populates="account")


class AccountInfo(Base):
    __tablename__ = "account_info"

    account_id = Column(String, ForeignKey("accounts.account_id"), primary_key=True)
    account_number = Column(String, nullable=True)
    leverage = Column(Integer, nullable=True)
    server = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    balance = Column(Float, nullable=True)
    equity = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="info")


class AccountCredentials(Base):
    __tablename__ = "account_credentials"

    account_id = Column(String, ForeignKey("accounts.account_id"), primary_key=True)
    login = Column(String, nullable=True)
    server = Column(String, nullable=True)
    password_encrypted = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="credentials")


class Magic(Base):
    __tablename__ = "magics"

    id = Column(Integer, autoincrement=False)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    label = Column(String, nullable=True)

    account = relationship("Account", back_populates="magics")
    group_links = relationship("MagicGroupAssignment", back_populates="magic")

    __table_args__ = (
        PrimaryKeyConstraint("account_id", "id", name="pk_magics"),
        Index("ix_magics_account_id", "account_id"),
    )


class MagicGroup(Base):
    __tablename__ = "magic_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    name = Column(String, nullable=False)
    label2 = Column(String, nullable=True)
    font_color = Column(String, nullable=True)
    fill_color = Column(String, nullable=True)

    account = relationship("Account", back_populates="groups")
    assignments = relationship("MagicGroupAssignment", back_populates="group")

    __table_args__ = (Index("ix_magic_groups_account_id", "account_id"),)


class MagicGroupAssignment(Base):
    __tablename__ = "magic_group_assignments"

    account_id = Column(String, ForeignKey("accounts.account_id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("magic_groups.id"), primary_key=True)
    magic_id = Column(Integer, primary_key=True)

    group = relationship("MagicGroup", back_populates="assignments")
    magic = relationship("Magic", back_populates="group_links")

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "magic_id"],
            ["magics.account_id", "magics.id"],
            name="fk_magic_group_assignments_magics",
        ),
    )


class Deal(Base):
    __tablename__ = "deals"

    ticket_id = Column(Integer, autoincrement=False)
    position_id = Column(Integer, nullable=False, index=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False, index=True)
    magic = Column(Integer, nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=True)
    volume = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    entry_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    swap = Column(Float, nullable=True)
    comment = Column(String, nullable=True)
    is_closed = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="deals")
    drawdown = relationship("DealDrawdown", uselist=False, back_populates="deal")

    __table_args__ = (
        PrimaryKeyConstraint("account_id", "ticket_id", name="pk_deals"),
        Index("ix_deals_account_time", "account_id", "entry_time"),
        Index("ix_deals_account_exit", "account_id", "exit_time"),
    )


class DealDrawdown(Base):
    __tablename__ = "deal_drawdowns"

    account_id = Column(String, primary_key=True)
    ticket_id = Column(Integer, primary_key=True)
    max_drawdown_points = Column(Float, nullable=True)
    max_drawdown_currency = Column(Float, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "ticket_id"],
            ["deals.account_id", "deals.ticket_id"],
            name="fk_deal_drawdowns_deals",
        ),
    )

    deal = relationship("Deal", back_populates="drawdown")


class Position(Base):
    __tablename__ = "positions"

    position_id = Column(Integer, autoincrement=False)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False, index=True)
    magic = Column(Integer, nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=True)
    volume = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    entry_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    swap = Column(Float, nullable=True)
    is_open = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="positions")

    __table_args__ = (
        PrimaryKeyConstraint("account_id", "position_id", name="pk_positions"),
    )


class TickRange(Base):
    __tablename__ = "tick_ranges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    first_tick_time = Column(Integer, nullable=True)
    last_tick_time = Column(Integer, nullable=True)
    tick_count = Column(Integer, nullable=True)

    __table_args__ = (Index("ix_tick_ranges_server_symbol", "server", "symbol"),)


class TickBatch(Base):
    __tablename__ = "tick_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    day = Column(String, nullable=False)
    compressed_blob = Column(String, nullable=True)
    tick_count = Column(Integer, nullable=True)

    __table_args__ = (Index("ix_tick_batches_server_symbol", "server", "symbol"),)
