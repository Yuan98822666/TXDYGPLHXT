import requests
import json
import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class BaseBlock(Base):
    __tablename__ = 'base_block'
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_code = Column(String(10))
    block_name = Column(String(100))
    block_type = Column(String(2)) # 'HY' for industry, 'GN' for concept
    block_stock_count = Column(Integer)
    update_time = Column(DateTime)

engine = create_engine('sqlite:///E:\\Python Project\\TXDYGPLHXT\\blocks.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def fetch_block_data(api_url, block_type):
    page = 1
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    while True:
        url = api_url.replace('pn=1', f'pn={page}')
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json_str = response.text[response.text.find('(')+1:response.text.rfind(')')]
            data = json.loads(json_str)
            if 'data' not in data or 'diff' not in data['data']:
                break
            for row in data['data']['diff']:
                block_code = row[0] if len(row) > 0 else ''
                block_name = row[1] if len(row) > 1 else ''
                stock_count = int(row[15]) if len(row) > 15 else 0
                new_block = BaseBlock(
                    block_code=block_code,
                    block_name=block_name,
                    block_type=block_type,
                    block_stock_count=stock_count,
                    update_time=datetime.datetime.now()
                )
                session.add(new_block)
            session.commit()
            page += 1
        except Exception as e:
            print(f"Error on page {page}: {str(e)}")
            break

industry_url = "https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery1123023271425959309378_1773898540757&fid=f62&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&ut=8dec03ba335b81bf4ebdf7b29ec27d15&fs=m%3A90+s%3A4&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69%2Cf72%2Cf75%2Cf78%2Cf81%2Cf84%2Cf87%2Cf204%2Cf205%2Cf124%2Cf1%2Cf13"
concept_url = "https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery1123023271425959309378_1773898540751&fid=f62&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&ut=8dec03ba335b81bf4ebdf7b29ec27d15&fs=m%3A90+t%3A3&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69%2Cf72%2Cf75%2Cf78%2Cf81%2Cf84%2Cf87%2Cf204%2Cf205%2Cf124%2Cf1%2Cf13"

fetch_block_data(industry_url, 'HY')
fetch_block_data(concept_url, 'GN')
print("数据下载完成！")