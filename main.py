import importlib
import json
import logging
import os
import time
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import kociemba

import contextlib
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    DateTime,
    Text,
    String,
)
from props import props 

app = FastAPI()
# CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(
    props["SQLALCHEMY_DATABASE_URI"],  # SQLAlchemy 数据库连接串，格式见下面
    # echo=bool(props.SQLALCHEMY_ECHO),  # 是不是要把所执行的SQL打印出来，一般用于调试
    # pool_size=int(props.SQLALCHEMY_POOL_SIZE),  # 连接池大小
    # max_overflow=int(props.SQLALCHEMY_POOL_MAX_SIZE),  # 连接池最大的大小
    # pool_recycle=int(props.SQLALCHEMY_POOL_RECYCLE),  # 多久时间主动回收连接，见下注释
)
Session = sessionmaker(bind=engine)
Base = declarative_base(engine)


@contextlib.contextmanager
def get_session():
    s = Session()
    try:
        yield s
        s.commit()
    except Exception as e:
        s.rollback()
        raise e
    finally:
        s.close()


class User(Base):
    __tablename__ = "hp_user"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, unique=True)

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict


class Formula(Base):
    __tablename__ = "hp_formula"
    
    id = Column(Integer, primary_key=True)
    technology = Column(String(32), nullable=False)
    kind = Column(String(32), nullable=False)
    detail = Column(Text, nullable=False)
    create_time = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_update_time = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now, index=True)

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())

@app.post("/v1/cube/solve/{content}")
async def query(content: str, params: Optional[dict] = {}):
    try:
        result = kociemba.solve(content)
        return {
            "code": 1,
            "message": "查询成功",
            "timestamp": int(round(time.time() * 1000)),
            "result": result
        }
    except:
        log.exception("查询异常")
        return {
            "code": 9,
            "message": "查询失败",
            "timestamp": int(round(time.time() * 1000))
        }


@app.post("/v1/user/find/{phone}")
async def formula_save(phone: str, params: Optional[dict] = {}):
    try:
        with get_session() as s:
            user = s.query(User).filter_by(phone=phone).first()
            if user:
                user = user.to_dict()
            return {
                "code": 1,
                "message": "查询成功",
                "timestamp": int(round(time.time() * 1000)),
                "result": user
            }
    except:
        log.exception("查询异常")
        return {
            "code": 9,
            "message": "查询失败",
            "timestamp": int(round(time.time() * 1000))
        }

@app.post("/v1/formula/count")
async def formula_count(params: Optional[dict] = {}):
    try:
        with get_session() as s:
            total = s.query(Formula).count()
            return {
                "code": 1,
                "message": "查询成功",
                "timestamp": int(round(time.time() * 1000)),
                "result": {
                    "total": total
                }
            }
    except:
        log.exception("查询异常")
        return {
            "code": 9,
            "message": "查询失败",
            "timestamp": int(round(time.time() * 1000))
        }


@app.post("/v1/formula/save/{id}")
async def formula_save(id: int, params: Optional[dict] = {}):
    try:
        with get_session() as s:
            formula = s.query(Formula).filter(Formula.id==id).first()
            if formula:
                s.query(Formula).filter(Formula.id==id).update(params)
            else: 
                formula = Formula(id=id,technology=params['technology'], kind=params['kind'], detail=params['detail'])
                s.add(formula)
                s.commit()
        return {
            "code": 1,
            "message": "保存成功",
            "timestamp": int(round(time.time() * 1000))
        }
    except:
        log.exception("保存异常")
        return {
            "code": 9,
            "message": "保存失败",
            "timestamp": int(round(time.time() * 1000))
        }


@app.post("/v1/formula/get/{id}")
async def formula_get(id: int, params: Optional[dict] = {}):
    try:
        with get_session() as s:
            formula = s.query(Formula).filter(Formula.id==id).first()
            if formula:
                formula = formula.to_dict()
            return {
                "code": 1,
                "message": "查询成功",
                "timestamp": int(round(time.time() * 1000)),
                "result": formula
            }
    except:
        log.exception("查询异常")
        return {
            "code": 9,
            "message": "查询失败",
            "timestamp": int(round(time.time() * 1000))
        }


@app.post("/v1/formula/delete/{id}")
async def formula_delete(id: int, params: Optional[dict] = {}):
    try:
        with get_session() as s:
            formula = s.query(Formula).filter(Formula.id==id).first()
            if formula:
                s.delete(formula)
                s.commit()
            return {
                "code": 1,
                "message": "删除成功",
                "timestamp": int(round(time.time() * 1000))
            }
    except:
        log.exception("查询异常")
        return {
            "code": 9,
            "message": "删除失败",
            "timestamp": int(round(time.time() * 1000))
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
