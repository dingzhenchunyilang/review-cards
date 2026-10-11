"""Idempotent sample-data seeder: `python -m app.seed`."""
from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Card, Category

SAMPLES: dict[str, list[tuple[str, str]]] = {
    "Redis": [
        (
            "Redis 的持久化有哪几种方式？",
            "- **RDB**：定时快照，恢复快，但可能丢失最后一次快照后的数据\n"
            "- **AOF**：记录每条写命令，数据更安全，文件更大\n"
            "- 4.0 之后可用**混合持久化**，兼顾恢复速度与安全",
        ),
        (
            "Redis 为什么这么快？",
            "1. 数据在内存中\n"
            "2. 单线程处理命令，避免上下文切换\n"
            "3. IO 多路复用\n"
            "4. 高效的数据结构，如跳表、压缩列表",
        ),
    ],
    "MySQL": [
        (
            "MySQL 索引为什么用 B+ 树？",
            "非叶子节点只存键，树更矮，磁盘 IO 更少；叶子节点用链表相连，**范围查询**很高效。\n"
            "```sql\nSELECT * FROM user WHERE age BETWEEN 20 AND 30;\n```",
        ),
        (
            "什么是最左前缀原则？",
            "联合索引 `(a,b,c)` 只能从最左列开始匹配：`a`、`a,b`、`a,b,c` 可用索引，单独查 `b` 则不行。",
        ),
    ],
    "Java 并发": [
        (
            "synchronized 和 ReentrantLock 有什么区别？",
            "- synchronized 是关键字，自动释放锁\n"
            "- ReentrantLock 是类，支持**可中断、公平锁、条件变量**\n"
            "- 需要在 finally 中手动 `unlock()`",
        ),
    ],
}


def seed() -> None:
    init_db()
    created_cats = 0
    created_cards = 0

    with SessionLocal() as db:
        for name, cards in SAMPLES.items():
            category = db.scalar(select(Category).where(Category.name == name))
            if category is None:
                category = Category(name=name)
                db.add(category)
                db.flush()
                created_cats += 1

            for question, answer in cards:
                exists = db.scalar(
                    select(Card).where(
                        Card.question == question, Card.category_id == category.id
                    )
                )
                if exists is None:
                    db.add(
                        Card(category_id=category.id, question=question, answer=answer)
                    )
                    created_cards += 1

        db.commit()

    print(f"seed done: +{created_cats} categories, +{created_cards} cards")


if __name__ == "__main__":
    seed()
