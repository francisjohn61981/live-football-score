from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
from datetime import datetime
from auth import create_access_token, check_token
import uuid
import sqlalchemy
from databases import Database
from contextlib import asynccontextmanager

# --------------------------- #
# Database setup
# --------------------------- #
DATABASE_URL = "postgresql+asyncpg://postgres:admin@localhost:5432/scorelive"

database = Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

matches_table = sqlalchemy.Table(
    "matches",
    metadata,
    sqlalchemy.Column("matchid", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("hometeam", sqlalchemy.String),
    sqlalchemy.Column("awayteam", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

goals_table = sqlalchemy.Table(
    "goals",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("matchid", sqlalchemy.String, sqlalchemy.ForeignKey("matches.matchid")),
    sqlalchemy.Column("minute", sqlalchemy.Integer),
    sqlalchemy.Column("scorer", sqlalchemy.String),
    sqlalchemy.Column("team", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(str(DATABASE_URL).replace("+asyncpg", ""))
metadata.create_all(engine)

# --------------------------- #
# Startup / Shutdown events
# --------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await database.connect()
        print("✅ Connected to the database.")
        yield
    finally:
        await database.disconnect()
        print("🛑 Disconnected from the database.")

# --------------------------- #
# FastAPI setup
# --------------------------- #
app = FastAPI(
    title="ScoreLive",
    description="To check and update football match scores",
    version="2.0",
    lifespan=lifespan
)

# --------------------------- #
# Pydantic models
# --------------------------- #
class Goal(BaseModel):
    minute: int
    scorer: str
    team: str

class Match(BaseModel):
    matchid: str
    Hometeam: str
    Awayteam: str
    goals: List[Goal] = []

# --------------------------- #
# Routes
# --------------------------- #
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to ScoreLive"}

@app.get("/token")
async def login_for_access_token(username: str):
    token = await create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer"}

# Protected route
@app.post("/newmatch", tags=["Update"])
async def create_match(
    Hometeam: str,
    Awayteam: str,
    token: Annotated[str, Depends(check_token)]
):
    match_uuid = str(uuid.uuid4())
    query = matches_table.insert().values(
        matchid=match_uuid, hometeam=Hometeam, awayteam=Awayteam
    )
    await database.execute(query)

    return {
        "message": "New match created successfully",
        "matchid": match_uuid,
        "Hometeam": Hometeam,
        "Awayteam": Awayteam,
    }

@app.post("/goalscored", tags=["Update"])
async def goal_scored(matchid: str, minute: int, scorer: str, team: str):
    # Check match exists
    match_query = matches_table.select().where(matches_table.c.matchid == matchid)
    match = await database.fetch_one(match_query)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    query = goals_table.insert().values(
        matchid=matchid, minute=minute, scorer=scorer, team=team
    )
    await database.execute(query)

    return {"message": "Goal recorded", "scorer": scorer, "team": team}

@app.get("/livematches/{matchid}", tags=["Matches"])
async def read_match(matchid: str):
    match_query = matches_table.select().where(matches_table.c.matchid == matchid)
    match = await database.fetch_one(match_query)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    goals_query = goals_table.select().where(goals_table.c.matchid == matchid)
    goals = await database.fetch_all(goals_query)

    return {
        "matchid": match["matchid"],
        "Hometeam": match["hometeam"],
        "Awayteam": match["awayteam"],
        "goals": goals,
    }

@app.get("/get_all_matches", tags=["Matches"])
async def get_all_matches():
    query = matches_table.select()
    rows = await database.fetch_all(query)
    return {"matches": rows}

@app.get("/score", tags=["Aggregate"])
async def aggregate_score(matchid: str):
    goals_query = goals_table.select().where(goals_table.c.matchid == matchid)
    goals = await database.fetch_all(goals_query)

    if not goals:
        raise HTTPException(status_code=404, detail="No goals found for match")

    match_query = matches_table.select().where(matches_table.c.matchid == matchid)
    match = await database.fetch_one(match_query)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    home_goals = sum(1 for g in goals if g["team"] == match["hometeam"])
    away_goals = sum(1 for g in goals if g["team"] == match["awayteam"])

    return {f"{match['hometeam']} vs {match['awayteam']}": f"{home_goals} - {away_goals}"}
