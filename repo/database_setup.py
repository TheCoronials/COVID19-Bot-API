import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_identifier = Column(String(250), nullable=False)
    name = Column(String(250), nullable=True)
    id_number = Column(String(10), nullable=True)
    bankaccounts = relationship("BankAccount")
    reg_date = Column(DateTime, default=datetime.datetime.utcnow)


class BankAccount(Base):

    __tablename__ = 'bankacc'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    bank = Column(String(50))
    accno = Column(String(15))
    branch = Column(String(6))
    reg_date = Column(DateTime, default=datetime.datetime.utcnow)


# Creates a create_engine instance at the bottom of the file
engine = create_engine('sqlite:///coronials-collection.db')
Base.metadata.create_all(engine)
