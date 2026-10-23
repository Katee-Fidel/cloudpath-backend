import json
from datetime import date, timedelta
from .db import db
from .content import TOPICS, BANK

def save_session(user, kind, topic, payload):
    with db() as c:
        return c.execute("INSERT INTO sessions(user_id,kind,topic,payload) VALUES(?,?,?,?) RETURNING id", (user,kind,topic,json.dumps(payload))).fetchone()["id"]

def readiness(user):
    with db() as c:
        rows = c.execute("SELECT topic, correct FROM answers WHERE user_id=? ORDER BY id DESC LIMIT 90", (user,)).fetchall()
    topics = []
    for key, meta in TOPICS.items():
        answers = [r["correct"] for r in rows if r["topic"]==key]
        topics.append({"id":key, **meta, "attempts":len(answers), "accuracy":round(100*sum(answers)/len(answers),1) if answers else None})
    estimate = round(sum((t["accuracy"] or 0)*t["weight"] for t in topics),1)
    sufficient = all(t["attempts"]>=10 for t in topics)
    return {"topics":topics,"practice_estimate":estimate,"sufficient_evidence":sufficient,"status":"Keep practising" if sufficient else "Collecting evidence", "note":"Heuristic weighted practice accuracy, not an official exam score or pass prediction. Uses last 90 answers; repeated practice can inflate it."}

def seed_cards(user):
    with db() as c:
        for topic, bank in BANK.items():
            for q,opts,answer,explanation in bank:
                c.execute("INSERT INTO cards(user_id,topic,front,back,due) VALUES(?,?,?,?,?) ON CONFLICT(user_id,front) DO NOTHING",(user,topic,q,opts[answer]+". "+explanation,date.today().isoformat()))

def make_plan(user, request):
    days = (request.exam_date-date.today()).days
    if days <= 0:
        from fastapi import HTTPException
        raise HTTPException(422,"Choose a future exam date")
    if days > 365:
        from fastapi import HTTPException
        raise HTTPException(422,"Choose an exam date within the next year")
    stats = readiness(user)["topics"]
    priorities = {t["id"]:t["weight"]*(2-(t["accuracy"] or 0)/100)*(1.5 if t["id"] in request.weak_topics else 1) for t in stats}
    allocated = {key:0.0 for key in priorities}
    sessions=[]
    # Weighted fair allocation: weakest domains recur more, all domains receive time.
    for n in range(days):
        topic=min(priorities,key=lambda k:allocated[k]/priorities[k])
        minutes=round(request.hours_per_week*60/7,1)
        allocated[topic]+=minutes
        sessions.append({"date":(date.today()+timedelta(days=n)).isoformat(),"topic":topic,"minutes":minutes,"activity":"Review notes, practise questions, and recall due flashcards"})
    return {"exam_date":str(request.exam_date),"hours_per_week":request.hours_per_week,"sessions":sessions,"topic_minutes":allocated}
