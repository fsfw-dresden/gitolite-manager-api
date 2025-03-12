import uvicorn
from fastapi.responses import RedirectResponse
from app import app

@app.get("/", include_in_schema=False)
async def root():
    """
    Redirect to the Swagger UI documentation
    """
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
