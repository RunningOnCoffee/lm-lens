@echo off
if "%1"=="up" docker compose up --build -d
if "%1"=="down" docker compose down
if "%1"=="logs" docker compose logs -f
if "%1"=="logs-api" docker compose logs -f lm-lens-api
if "%1"=="logs-ui" docker compose logs -f lm-lens-ui
if "%1"=="test" docker compose exec lm-lens-api pytest -v
if "%1"=="db-shell" docker compose exec lm-lens-db psql -U lm-lens -d lm-lens
if "%1"=="reset" docker compose down -v && docker compose up --build -d
if "%1"=="build" docker compose build
if "%1"=="" (
    echo LM Lens Commands:
    echo   lens up        Build and start all services
    echo   lens down      Stop all services
    echo   lens logs      Tail all service logs
    echo   lens logs-api  Tail backend logs only
    echo   lens logs-ui   Tail frontend logs only
    echo   lens test      Run backend pytest
    echo   lens db-shell  Open psql shell
    echo   lens reset     Destroy volumes and rebuild
    echo   lens build     Build without starting
)
