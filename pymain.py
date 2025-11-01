from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from typing import List, Annotated
import uuid
from auth import create_access_token, check_token

app = FastAPI(
    title="ScoreLive",
    description="To check and update football match scores",
    version="1.0"
)

class Goal(BaseModel):
    minute: int
    scorer: str
    team: str

class Match(BaseModel):
    matchid: str
    Hometeam: str
    Awayteam: str
    goals: List[Goal]

matches: List[Match] = []

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to ScoreLive"}

@app.get("/token")
def login_for_access_token(username:str):
    token=create_access_token({"sub":username})
    return {"access_token":token, "token_type": "bearer"}

@app.get("/livematches/{id}", tags=["Matches"])
def read_list(id: str):
    for existing_match in matches:
        if existing_match.matchid == id:
            return {"matches" : existing_match}
    return {"message" : "invalid request"}

#--------protected routes-----------------------#
@app.post("/newmatch", tags=["Update"])
def create_match(Hometeam: str, Awayteam:str ,
                 token_data: dict = Depends(check_token)):
    match_uuid = str(uuid.uuid4())
    new_match = Match(
        matchid=match_uuid,
        Hometeam=Hometeam,
        Awayteam=Awayteam,
        goals=[]
    )
    
    matches.append(new_match)
    return {
        "message": "New match created successfully",
        "matchid": match_uuid,
        "Hometeam": Hometeam,
        "Awayteam": Awayteam
    }
#--------protected routes-----------------------#

@app.get("/get_all_matches", tags=["Matches"])
def get_all_matches():
    for existing_match in matches:
        return {"matches" : existing_match}
    return {"message" : "invalid request"}


@app.post("/goalscored", tags=["Update"])
def goal_scored(matchid:str, minute: int, scorer:str, team: str):
    for existing_match in matches:
        if existing_match.matchid==matchid:
            new_goal = Goal(
                minute=minute,
                scorer=scorer,
                team=team
            )
            existing_match.goals.append(new_goal)
    return {"message" : "new goal updated", "scorer" : scorer}

@app.get("/score", tags=["aggregatescore"])
def aggregate_score(matchid:str):
    for existing_match in matches:
        if existing_match.matchid==matchid:
            home_goals = sum(1 for g in existing_match.goals if g.team == existing_match.Hometeam)
            away_goals = sum(1 for g in existing_match.goals if g.team == existing_match.Awayteam)
            return {f"{existing_match.Hometeam} : {home_goals} - {existing_match.Awayteam} : {away_goals}"}
    return{"message": "invalid request"}