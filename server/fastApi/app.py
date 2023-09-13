from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from server.fastApi.publicApp import publicApp
from fastapi.middleware.cors import CORSMiddleware
from server.fastApi.privateApp import privateApp


app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/api", privateApp)
app.mount("/public", publicApp)



