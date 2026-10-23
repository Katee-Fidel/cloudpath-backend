import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import PurePath
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .db import db, init_db
from .auth import current_user, hasher, token_for, secret
from .schemas import Credentials, StudyRequest, QuizRequest, AnswerRequest, ReviewRequest, PlanRequest
from .documents import MAX_UPLOAD, parse_docx, retrieve
from .content import TOPICS
from .ai import generate
from .study import save_session, readiness, seed_cards, make_plan

@asynccontextmanager
async def lifespan(app):
    secret()
    init_db()
    yield

app = FastAPI(title="CloudPath — Unofficial AZ-900 Study API",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3000").split(","),allow_methods=["GET","POST","DELETE"],allow_headers=["Authorization","Content-Type"])

@app.get("/health")
def health():
    with db() as c: c.execute("SELECT 1")
    return {"status":"ok","ai_mode":os.getenv("AI_MODE","demo"),"unofficial":True}

@app.get("/topics")
def topics():
    return {"topics":TOPICS,"outline":"https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-900", "outline_date":"2026-07-20","unofficial":True}

@app.post("/auth/register",status_code=201)
def register(request: Credentials):
    password=hasher.hash(request.password)
    with db() as c:
        user=c.execute("INSERT INTO users(email,password) VALUES(?,?) ON CONFLICT(email) DO NOTHING RETURNING id",(request.email,password)).fetchone()
    if not user:
        raise HTTPException(409,"Account already exists")
    seed_cards(user["id"])
    return {"access_token":token_for(user["id"]),"token_type":"bearer"}

@app.post("/auth/login")
def login(request: Credentials):
    with db() as c:
        row=c.execute("SELECT * FROM users WHERE email=?",(request.email,)).fetchone()
    if not row or not hasher.verify(request.password,row["password"]):
        raise HTTPException(401,"Incorrect email or password")
    return {"access_token":token_for(row["id"]),"token_type":"bearer"}

@app.post("/documents",status_code=201)
async def upload(file: UploadFile=File(...), user=Depends(current_user)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(415,"Upload a .docx file")
    data=await file.read(MAX_UPLOAD+1)
    await file.close()
    if len(data)>MAX_UPLOAD: raise HTTPException(413,"Maximum upload size is 5 MiB")
    text=await asyncio.to_thread(parse_docx,data)
    name=PurePath(file.filename.replace("\\","/")).name[:200]
    with db() as c:
        doc=c.execute("INSERT INTO documents(user_id,name,text) VALUES(?,?,?) RETURNING id",(user,name,text)).fetchone()["id"]
    return {"id":doc,"name":name,"characters":len(text),"preview":text[:500]}

@app.get("/documents")
def documents(user=Depends(current_user)):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id,name,length(text) AS characters FROM documents WHERE user_id=? ORDER BY id DESC",(user,))]

@app.delete("/documents/{doc_id}",status_code=204)
def delete_document(doc_id:int,user=Depends(current_user)):
    with db() as c:
        if not c.execute("DELETE FROM documents WHERE id=? AND user_id=?",(doc_id,user)).rowcount:
            raise HTTPException(404,"Document not found")

def sources_for(request, user):
    if request.document_id is None: return []
    with db() as c:
        doc=c.execute("SELECT text FROM documents WHERE id=? AND user_id=?",(request.document_id,user)).fetchone()
    if not doc: raise HTTPException(404,"Document not found")
    return retrieve(doc["text"],request.prompt)

@app.post("/buddy")
async def buddy(request:StudyRequest,user=Depends(current_user)):
    sources=await asyncio.to_thread(sources_for,request,user)
    result=await generate("buddy",request,sources)
    payload={"request":request.model_dump(),**result,"sources":sources}
    session=await asyncio.to_thread(save_session,user,"buddy",request.topic,payload)
    return {"id":session,**payload}

@app.post("/quizzes",status_code=201)
async def create_quiz(request:QuizRequest,user=Depends(current_user)):
    sources=await asyncio.to_thread(sources_for,request,user)
    result=await generate("quiz",request,sources)
    payload={"request":request.model_dump(),**result,"sources":sources}
    session=await asyncio.to_thread(save_session,user,"quiz",request.topic,payload)
    return {"id":session,"topic":request.topic,"mode":result["mode"],"questions":[{"question":q["question"],"options":q["options"]} for q in result["questions"]]}

@app.post("/quizzes/{quiz_id}/answers")
def answer(quiz_id:int,request:AnswerRequest,user=Depends(current_user)):
    with db() as c:
        session=c.execute("SELECT * FROM sessions WHERE id=? AND user_id=? AND kind='quiz'",(quiz_id,user)).fetchone()
        if not session: raise HTTPException(404,"Quiz not found")
        qs=json.loads(session["payload"])["questions"]
        if request.question_index>=len(qs): raise HTTPException(422,"Question index out of range")
        q=qs[request.question_index]
        correct=request.selected==q["answer"]
        inserted=c.execute("INSERT INTO answers(user_id,quiz_id,question_index,topic,correct) VALUES(?,?,?,?,?) ON CONFLICT(user_id,quiz_id,question_index) DO NOTHING RETURNING id",(user,quiz_id,request.question_index,session["topic"],int(correct))).fetchone()
        if not inserted:
            raise HTTPException(409,"This question has already been answered")
    return {"correct":correct,"answer":q["answer"],"explanation":q["explanation"]}

@app.get("/readiness")
def get_readiness(user=Depends(current_user)): return readiness(user)

@app.get("/flashcards")
def cards(user=Depends(current_user)):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id,topic,front,back,due,repetitions,interval_days FROM cards WHERE user_id=? AND due<=? ORDER BY repetitions,due,id",(user,date.today().isoformat()))]

@app.post("/flashcards/{card_id}/review")
def review(card_id:int,request:ReviewRequest,user=Depends(current_user)):
    with db() as c:
        card=c.execute("SELECT * FROM cards WHERE id=? AND user_id=?",(card_id,user)).fetchone()
        if not card: raise HTTPException(404,"Card not found")
        if card["due"]>date.today().isoformat(): raise HTTPException(409,"Card is not due yet")
        reps=card["repetitions"]+1 if request.remembered else 0
        interval=(1 if reps==1 else 3 if reps==2 else min(180,card["interval_days"]*2)) if request.remembered else 0
        due=(date.today()+timedelta(days=interval)).isoformat()
        c.execute("UPDATE cards SET repetitions=?,interval_days=?,due=? WHERE id=?",(reps,interval,due,card_id))
    return {"due":due,"interval_days":interval,"repetitions":reps}

@app.post("/plans",status_code=201)
def plan(request:PlanRequest,user=Depends(current_user)):
    payload=make_plan(user,request)
    return {"id":save_session(user,"plan","all",payload),**payload}

@app.get("/history")
def history(user=Depends(current_user)):
    with db() as c:
        rows=c.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY id DESC LIMIT 100",(user,)).fetchall()
        output=[]
        for row in rows:
            item=dict(row);item.pop("user_id")
            item["payload"]=json.loads(item["payload"])
            if item["kind"]=="quiz":
                # History must not disclose answers to unfinished quizzes.
                answered={r["question_index"] for r in c.execute("SELECT question_index FROM answers WHERE user_id=? AND quiz_id=?",(user,item["id"]))}
                for index,q in enumerate(item["payload"]["questions"]):
                    if index not in answered:
                        q.pop("answer",None);q.pop("explanation",None)
            output.append(item)
        return output

@app.get("/reminders")
def reminders(user=Depends(current_user)):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT day,message FROM reminders WHERE user_id=? ORDER BY day DESC LIMIT 30",(user,))]
