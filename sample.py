import jwt
from datetime import datetime, timedelta
from fastapi import OAuth2PasswordBearer, Depends, HTTPException, status
from typing import Annotated

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "secret"
def create_token(data: dict):
    data_token = data.copy()
    data_token.update({"exp": datetime.utcnow() + timedelta(minutes=60)})
    return jwt.encode(data_token, SECRET_KEY, algorithm="HSA256" )

token_dependency = Annotated [str, Depends(oauth2_scheme)]

def check_token_validity(token: token_dependency):
    try:
        token.decode(token, SECRET_KEY, algorithms=["HSA256"])
        return True
    except jwt.ExpiredSignatureErrorSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")