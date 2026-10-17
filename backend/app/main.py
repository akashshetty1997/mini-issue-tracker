from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Issue Tracker API")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
