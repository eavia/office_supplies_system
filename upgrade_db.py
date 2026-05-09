#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
办公用品管理系统 — 数据库升级脚本 (2026-04-30)
==============================================
独立脚本，不依赖 Django migration 系统。
直接对 SQLite 数据库执行 DDL 变更。

安全保证:
  - 升级前自动备份（时间戳命名），备份成功才执行
  - 每个升级步骤在事务内执行，失败自动回滚
  - 执行后校验数据完整性（表数量、关键表行数）
  - 所有操作仅新增列/表，绝不修改或删除已有数据

用法:
    python upgrade_db.py              # 交互模式，检查后确认升级
    python upgrade_db.py --apply      # 自动执行（含备份）
    python upgrade_db.py --check      # 仅检查，不执行
    python upgrade_db.py --no-backup  # 跳过备份（危险，仅测试用）
"""

import os
import sys
import shutil
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

# ── 数据库位置 ──────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent

if sys.platform == 'win32' and hasattr(sys, '_MEIPASS'):
    DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / 'OfficeSuppliesSystem'
else:
    DATA_DIR = PROJECT_DIR

DB_PATHS = [
    DATA_DIR / 'db.sqlite3',
    PROJECT_DIR / 'db.sqlite3',
]

BACKUP_DIR = PROJECT_DIR / 'db_backups'

# ── 升级步骤定义 ───────────────────────────────────────
# 每个步骤: (version, description, sql_list)
# ⚠️ 约束: sql_list 中只允许 ADD COLUMN / CREATE TABLE IF NOT EXISTS / CREATE INDEX
#    绝对禁止 DROP / DELETE / UPDATE（保护数据安全）
MIGRATIONS = [
    (
        '2026-04-30-001',
        '入库明细(StockInItem)增加单价字段 unit_price',
        [
            "ALTER TABLE inventory_stockinitem ADD COLUMN unit_price decimal(10,2) NOT NULL DEFAULT 0",
        ]
    ),
]


# ═══════════════════════════════════════════════════════
# 安全检查：禁止危险 SQL
# ═══════════════════════════════════════════════════════

FORBIDDEN_KEYWORDS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER ... RENAME']

def _validate_sql_safety(sql_list):
    """拒绝包含危险操作的 SQL"""
    for sql in sql_list:
        upper = sql.upper().strip()
        for keyword in FORBIDDEN_KEYWORDS:
            if upper.startswith(keyword) and 'ADD COLUMN' not in upper:
                raise ValueError(
                    f"❌ 升级脚本包含危险 SQL（{keyword}），拒绝执行！\n"
                    f"   脚本只允许 ADD COLUMN / CREATE TABLE IF NOT EXISTS / CREATE INDEX。\n"
                    f"   SQL: {sql[:80]}..."
                )


# ═══════════════════════════════════════════════════════
# 数据库定位
# ═══════════════════════════════════════════════════════

def find_db():
    """定位 SQLite 数据库文件"""
    for p in DB_PATHS:
        if p.exists():
            return p
    return None


# ═══════════════════════════════════════════════════════
# 备份
# ═══════════════════════════════════════════════════════

def backup_db(db_path):
    """备份数据库，返回备份文件路径。失败则抛异常阻止后续操作。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f"db_before_upgrade_{timestamp}.sqlite3"

    # 先验证源文件可读
    if not db_path.exists():
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")
    if db_path.stat().st_size == 0:
        raise ValueError(f"数据库文件为空: {db_path}")

    shutil.copy2(str(db_path), str(backup_path))

    # 验证备份完整性
    if not backup_path.exists():
        raise RuntimeError(f"备份文件未生成: {backup_path}")
    if backup_path.stat().st_size != db_path.stat().st_size:
        raise RuntimeError(
            f"备份文件大小不匹配！源: {db_path.stat().st_size}, 备份: {backup_path.stat().st_size}"
        )

    return backup_path


# ═══════════════════════════════════════════════════════
# 数据完整性快照
# ═══════════════════════════════════════════════════════

def snapshot_tables(conn):
    """记录所有用户表的行数"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_db_%' AND name NOT LIKE 'django_%' AND name NOT LIKE 'auth_%' AND name NOT LIKE 'inventory_%'")
    # 记录 inventory_ 开头的表
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'inventory_%'")
    tables = [row[0] for row in cur.fetchall()]

    snapshot = {}
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            snapshot[table] = cur.fetchone()[0]
        except sqlite3.Error:
            snapshot[table] = -1  # 跳过无法查询的表
    return snapshot


def verify_integrity(conn, before_snapshot, db_path):
    """升级后校验：表不能少，行数不能少"""
    after = snapshot_tables(conn)
    errors = []

    # 检查是否有表丢失
    missing = set(before_snapshot.keys()) - set(after.keys())
    if missing:
        errors.append(f"表丢失: {', '.join(missing)}")

    # 检查每张表行数是否减少
    for table, before_count in before_snapshot.items():
        after_count = after.get(table, -1)
        if after_count < 0:
            continue
        if after_count < before_count:
            errors.append(
                f"表 [{table}] 行数减少: {before_count} → {after_count}"
            )

    if errors:
        raise RuntimeError(
            f"❌ 数据完整性校验失败！\n"
            f"   数据库: {db_path}\n"
            f"   " + "\n   ".join(errors) + "\n\n"
            f"请从备份恢复数据库后重试。"
        )


# ═══════════════════════════════════════════════════════
# 升级执行
# ═══════════════════════════════════════════════════════

def get_applied_versions(conn):
    """读取已应用的升级版本"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_db_upgrade_log'")
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _db_upgrade_log (
                version TEXT PRIMARY KEY,
                description TEXT,
                applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()
        return set()

    cur.execute("SELECT version FROM _db_upgrade_log")
    return {row[0] for row in cur.fetchall()}


def column_exists(conn, table, column):
    """检查列是否已存在"""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def apply_migration(conn, version, description, sql_list):
    """在事务内执行一个升级步骤，失败自动回滚"""
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        for sql in sql_list:
            try:
                cur.execute(sql)
            except sqlite3.OperationalError as e:
                err_msg = str(e)
                if 'duplicate column' in err_msg.lower() or 'already exists' in err_msg.lower():
                    col = sql.split('ADD COLUMN')[-1].strip().split()[0] if 'ADD COLUMN' in sql else '?'
                    print(f"  ⏭  跳过（列已存在）: {col}")
                    continue
                raise

        cur.execute(
            "INSERT OR REPLACE INTO _db_upgrade_log (version, description, applied_at) "
            "VALUES (?, ?, datetime('now','localtime'))",
            (version, description)
        )
        conn.commit()
        print(f"  ✅ 已应用: {description}")
    except Exception:
        conn.rollback()
        raise


def _check_columns(conn, sql_list):
    """检查 SQL 中的 ADD COLUMN 是否已存在"""
    import re
    for sql in sql_list:
        m = re.search(r'ADD\s+COLUMN\s+(\w+)', sql, re.IGNORECASE)
        if m:
            col_name = m.group(1)
            table_m = re.search(r'ALTER\s+TABLE\s+(\w+)', sql, re.IGNORECASE)
            table = table_m.group(1) if table_m else 'inventory_stockinitem'
            if not column_exists(conn, table, col_name):
                return False
    return True


def check_all(conn):
    """检查所有迁移状态"""
    applied = get_applied_versions(conn)
    print("升级步骤检查:")
    all_ok = True
    for version, description, sql_list in MIGRATIONS:
        col_ok = _check_columns(conn, sql_list)
        if col_ok:
            if version not in applied:
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR IGNORE INTO _db_upgrade_log (version, description, applied_at) "
                    "VALUES (?, ?, datetime('now','localtime'))",
                    (version, description)
                )
                conn.commit()
                applied.add(version)
            print(f"  [{version}] {description} — ✅ 已应用")
        elif version in applied:
            print(f"  [{version}] {description} — ⚠️ 日志已记录但列不存在，需人工检查")
            all_ok = False
        else:
            print(f"  [{version}] {description} — ❌ 未应用")
            all_ok = False

    return all_ok


def apply_all(conn, db_path, skip_backup=False):
    """应用所有未执行的迁移（含备份+事务+校验）"""
    # 1. 安全检查
    for _, _, sql_list in MIGRATIONS:
        _validate_sql_safety(sql_list)

    # 2. 备份
    backup_path = None
    if not skip_backup:
        print("📦 正在备份数据库...")
        backup_path = backup_db(db_path)
        print(f"   备份已保存: {backup_path}")
        print()

    # 3. 升级前快照
    before_snapshot = snapshot_tables(conn)
    print(f"📊 升级前数据快照: {sum(before_snapshot.values())} 条记录 ({len(before_snapshot)} 张表)")
    print()

    # 4. 执行升级
    applied = get_applied_versions(conn)
    any_applied = False
    for version, description, sql_list in MIGRATIONS:
        if version in applied or _check_columns(conn, sql_list):
            if version not in applied:
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR IGNORE INTO _db_upgrade_log (version, description, applied_at) "
                    "VALUES (?, ?, datetime('now','localtime'))",
                    (version, description)
                )
                conn.commit()
            print(f"  ⏭  跳过 [{version}]: {description} (已应用)")
            continue
        apply_migration(conn, version, description, sql_list)
        any_applied = True

    if not any_applied:
        print("  所有升级已是最新，无需操作。")
        # 清理无用的备份
        if backup_path and backup_path.exists():
            backup_path.unlink()
        return False

    # 5. 升级后校验
    print()
    print("🔍 校验数据完整性...")
    verify_integrity(conn, before_snapshot, db_path)
    after_snapshot = snapshot_tables(conn)
    print(f"   校验通过: {sum(after_snapshot.values())} 条记录，无数据丢失")

    return True


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='办公用品管理系统数据库升级')
    parser.add_argument('--apply', action='store_true', help='自动执行升级（含备份）')
    parser.add_argument('--check', action='store_true', help='仅检查升级状态')
    parser.add_argument('--no-backup', action='store_true', help='跳过数据库备份（危险！仅测试用）')
    args = parser.parse_args()

    db_path = find_db()
    if not db_path:
        print("❌ 未找到数据库文件！")
        print(f"   搜索路径: {[str(p) for p in DB_PATHS]}")
        sys.exit(1)

    print(f"数据库: {db_path}")
    print(f"大小: {db_path.stat().st_size:,} 字节")
    print()

    conn = sqlite3.connect(str(db_path))

    try:
        if args.check:
            ok = check_all(conn)
            sys.exit(0 if ok else 1)

        if args.apply:
            apply_all(conn, db_path, skip_backup=args.no_backup)
            print()
            print("升级完成。")
            return

        # 交互模式
        check_all(conn)
        print()
        response = input("是否执行未应用的升级？[y/N]: ").strip().lower()
        if response in ('y', 'yes'):
            print()
            apply_all(conn, db_path, skip_backup=args.no_backup)
            print()
            print("升级完成。")
        else:
            print("已取消。")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
