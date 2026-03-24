from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseBlock(Base):
    __tablename__ = 'base_block'
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_code = Column(String(10))
    block_name = Column(String(100))
    block_type = Column(String(2))
    block_stock_count = Column(Integer)
    update_time = Column(DateTime)

engine = create_engine('sqlite:///E:\\Python Project\\TXDYGPLHXT\\blocks.db')
Session = sessionmaker(bind=engine)