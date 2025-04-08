from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
import logging
from app.database import Base, engine
from app.routes import user, cng, admin, book, ai, toll, stream
from fastapi.staticfiles import StaticFiles
# Create FastAPI app instance
app = FastAPI()
app.mount("/streams", StaticFiles(directory="streams"), name="streams")
# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware (for security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)


# Exception handlers


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"message": "Validation error", "details": exc.errors()},
    )

# Include the API routers
Base.metadata.create_all(bind=engine)

app.include_router(user.router)
app.include_router(cng.router)
app.include_router(admin.router)
app.include_router(book.router)
app.include_router(ai.router)
app.include_router(toll.router)
app.include_router(stream.router)


@app.get('/')
async def read_root():
    return {"message": "Hello, World!"}


@app.on_event("startup")
async def on_startup():
    # Initialize logging or other startup procedures
    logging.basicConfig(level=logging.INFO)
    logging.info("Application startup")

# Application shutdown event handler


@app.on_event("shutdown")
async def on_shutdown():
    # Clean up resources or other shutdown procedures
    logging.info("Application shutdown")
