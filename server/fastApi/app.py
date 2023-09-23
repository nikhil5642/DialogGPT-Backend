from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from server.fastApi.publicApi import publicApi
from server.fastApi.privateApi import privateApi


app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/api", privateApi)
app.mount("/public", publicApi)



