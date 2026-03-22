"""
通用数据库入库工具（适配已有项目风格）

功能说明：
- 提供通用的批量入库接口
- 支持 Base 数据的两阶段入库策略：
  1. 数据库为空时 → 全量插入
  2. 数据库有数据时 → 对比除 id 外所有字段，增量更新有变化的记录
- 使用 SQLAlchemy bulk_save_objects 提升性能
- 完整事务管理，失败自动回滚

设计原则：
- 与 snapshot_writer.py 保持一致的代码风格
- 防御性编程：空列表、空表等边界情况全覆盖
- 日志详细：入库统计清晰可查
"""

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import Type, TypeVar, Generic, List, Optional
from loguru import logger

T = TypeVar("T")


class UpsertHelper(Generic[T]):
    """
    通用入库工具，支持：
    - 全量入库（数据库为空时）
    - 增量更新（数据库有数据时，对比除 id 外所有字段）

    与 Base 数据模型的配合：
    - Base 数据（板块基础表等）需要精确的增量更新
    - Raw 数据（快照数据）只需全量追加，不需要更新
    """

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def _get_pk_name(self) -> str:
        """获取主键名"""
        mapper = inspect(self.model)
        pk = mapper.primary_key[0]
        return pk.name

    def _is_table_empty(self) -> bool:
        """检查表是否为空"""
        return self.session.query(self.model).first() is None

    def _get_existing_map(self, key_field: str) -> dict:
        """
        获取数据库中现有数据的映射

        参数:
            key_field: 用于匹配的关键字段名（如 block_code）

        返回:
            dict: {字段值: ORM对象} 的映射
        """
        rows = self.session.query(self.model).all()
        return {getattr(row, key_field): row for row in rows if getattr(row, key_field, None) is not None}

    def bulk_upsert(
        self,
        records: List[dict],
        key_field: str = "block_code",
    ) -> dict:
        """
        批量入库/更新（两阶段策略）

        策略1（数据库为空）：
            - 执行全量插入
            - 使用 bulk_save_objects，性能最优

        策略2（数据库有数据）：
            - 遍历每条新数据
            - key_field 相同 → 对比所有非关键字段，有变化则更新
            - key_field 不存在 → 视为新记录插入

        参数:
            records:    字典列表，每条数据
            key_field:  用于匹配现有记录的关键字段

        返回:
            dict: 操作统计 {inserted, updated, skipped, failed}
        """
        if not records:
            logger.warning(f"[{self.model.__tablename__}] records 为空，跳过入库")
            return {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

        stats = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

        if self._is_table_empty():
            # 阶段1：全量入库
            logger.info(
                f"[{self.model.__tablename__}] 【全量入库】表为空，"
                f"执行全量插入，共 {len(records)} 条"
            )
            try:
                objects = [self.model(**rec) for rec in records]
                self.session.bulk_save_objects(objects)
                self.session.commit()
                stats["inserted"] = len(records)
                logger.info(
                    f"[{self.model.__tablename__}] 【全量入库】成功 "
                    f"inserted={stats['inserted']}"
                )
            except Exception as e:
                self.session.rollback()
                logger.error(f"[{self.model.__tablename__}] 【全量入库】失败: {e}")
                stats["failed"] = len(records)
        else:
            # 阶段2：增量更新
            existing_map = self._get_existing_map(key_field)
            to_insert: List[dict] = []
            to_update: List[Session] = []  # 已加载到 session 的 ORM 对象

            for rec in records:
                key_val = rec.get(key_field)
                if key_val is None:
                    stats["skipped"] += 1
                    continue

                if key_val in existing_map:
                    # 已有记录：对比所有非关键字段
                    old_row = existing_map[key_val]
                    needs_update = False

                    for field, new_val in rec.items():
                        if field in (key_field, self._get_pk_name()):
                            continue
                        old_val = getattr(old_row, field, None)
                        if old_val != new_val:
                            needs_update = True
                            setattr(old_row, field, new_val)

                    if needs_update:
                        to_update.append(old_row)
                    else:
                        stats["skipped"] += 1
                else:
                    # 新记录待插入
                    to_insert.append(rec)

            # 执行更新
            if to_update:
                try:
                    for row in to_update:
                        self.session.merge(row)
                    self.session.commit()
                    stats["updated"] = len(to_update)
                    logger.info(
                        f"[{self.model.__tablename__}] 【增量更新】更新 "
                        f"{stats['updated']} 条"
                    )
                except Exception as e:
                    self.session.rollback()
                    logger.error(f"[{self.model.__tablename__}] 【增量更新】失败: {e}")
                    stats["failed"] += len(to_update)

            # 执行插入
            if to_insert:
                try:
                    objects = [self.model(**rec) for rec in to_insert]
                    self.session.bulk_save_objects(objects)
                    self.session.commit()
                    stats["inserted"] = len(to_insert)
                    logger.info(
                        f"[{self.model.__tablename__}] 【增量更新】新增插入 "
                        f"{stats['inserted']} 条"
                    )
                except Exception as e:
                    self.session.rollback()
                    logger.error(
                        f"[{self.model.__tablename__}] 【增量更新】新增失败: {e}"
                    )
                    stats["failed"] += len(to_insert)

        return stats
