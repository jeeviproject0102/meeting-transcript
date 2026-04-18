from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import meeting
from app.db.database import engine
from app.models import meeting as meeting_model

# Create tables automatically on startup
meeting_model.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Meeting Transcript Analyzer")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meeting.router, prefix="/api")

@app.get('/')
def root():
    return {'message': 'AI Meeting Transcript Analyzer API is running'}