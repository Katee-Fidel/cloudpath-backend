"""Run once a day, or --loop for the Compose worker. No outgoing messages."""
import argparse
import time
from datetime import date
from .db import db,init_db

def run_daily():
    init_db()
    today=date.today().isoformat()
    with db() as c:
        users=c.execute("SELECT id FROM users").fetchall()
        count=0
        for user in users:
            due=c.execute("SELECT COUNT(*) AS due_count FROM cards WHERE user_id=? AND due<=?",(user["id"],today)).fetchone()["due_count"]
            message=f"You have {due} flashcards due. Review a weak topic and try a short quiz."
            inserted=c.execute("INSERT INTO reminders(user_id,day,message) VALUES(?,?,?) ON CONFLICT(user_id,day) DO NOTHING RETURNING id",(user["id"],today,message)).fetchone()
            count+=inserted is not None
    return count

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--loop",action="store_true");args=parser.parse_args()
    while True:
        print(f"Created {run_daily()} daily reminders",flush=True)
        if not args.loop: break
        time.sleep(3600) # checks hourly; UNIQUE(user_id,day) makes writes daily/idempotent
