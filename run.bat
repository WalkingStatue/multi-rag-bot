@echo off

if "%1"=="install" (
    echo Installing backend dependencies...
    cd backend && pip install -r requirements.txt
    echo Installing frontend dependencies...
    cd ../frontend && npm install
    echo Dependencies installed successfully!
    goto :eof
)

if "%1"=="run" (
    echo Starting Multi-Bot RAG Platform...
    docker-compose up --build
    goto :eof
)

if "%1"=="stop" (
    echo Stopping application...
    docker-compose down
    goto :eof
)

if "%1"=="logs" (
    docker-compose logs -f
    goto :eof
)

if "%1"=="clean" (
    echo Cleaning up containers and volumes...
    docker-compose down -v
    docker system prune -f
    goto :eof
)

echo Usage: run.bat [install^|run^|stop^|logs^|clean]
echo.
echo Commands:
echo   install  - Install all dependencies
echo   run      - Start the entire application
echo   stop     - Stop the application
echo   logs     - View logs
echo   clean    - Clean up containers and volumes