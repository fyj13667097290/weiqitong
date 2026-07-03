#!/usr/bin/env python3
"""从免费API批量抓取驾考题库"""
import requests, sqlite3, time, random

DB = "/opt/jiaxiao/platform/admin/data.db"
API = "https://cn.apihz.cn/api/jiaotong/jiakao.php?id=88888888&key=88888888&type="

def fetch_and_import(subject="1", count=500):
    """抓取并导入科目一/四题库"""
    conn = sqlite3.connect(DB)
    imported = 0
    failed = 0

    for i in range(1, count + 50):  # 多抓一些以防重复
        try:
            resp = requests.get(f"{API}{subject}", timeout=8)
            data = resp.json()
            if data.get("code") != 200:
                failed += 1
                if failed > 10: break
                continue

            title = data.get("title","").strip()
            if not title: continue

            qtype = "judge" if len(data.get("opta","")) > 0 and not data.get("optb","") else "single"

            # 检查是否已存在
            existing = conn.execute("SELECT id FROM exam_questions WHERE title=?", [title]).fetchone()
            if existing: continue

            conn.execute("""
                INSERT INTO exam_questions (type,chapter,title,image,option_a,option_b,option_c,option_d,answer,explain)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, [
                qtype,
                "科目" + ("一" if subject=="1" else "四"),
                title,
                data.get("pic","") or None,
                data.get("opta","") or "",
                data.get("optb","") or "",
                data.get("optc","") or "",
                data.get("optd","") or "",
                data.get("answer",""),
                data.get("explain","") or data.get("explains","") or ""
            ])
            imported += 1
            failed = 0
            if imported % 50 == 0:
                print(f"  已导入 {imported} 题...")
            if imported >= count:
                break
            time.sleep(0.3 + random.random() * 0.5)
        except Exception as e:
            failed += 1
            if failed > 20:
                print(f"  连续失败过多，停止: {e}")
                break
            time.sleep(1)

    conn.commit()
    # 统计
    total = conn.execute("SELECT COUNT(*) FROM exam_questions WHERE is_active=1").fetchone()[0]
    by_type = conn.execute("SELECT chapter, COUNT(*) FROM exam_questions GROUP BY chapter").fetchall()
    conn.close()
    print(f"\n✅ 本次导入 {imported} 题")
    print(f"📊 题库总计 {total} 题")
    for ch, cnt in by_type:
        print(f"   {ch}: {cnt} 题")

if __name__ == "__main__":
    import sys
    subject = sys.argv[1] if len(sys.argv) > 1 else "1"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    print(f"🔍 开始抓取科目{'一' if subject=='1' else '四'}题库（目标 {count} 题）...")
    fetch_and_import(subject, count)
