param(
    [Parameter(Position=0)]
    [string]$Command
)

switch ($Command) {
    "install" {
        Write-Host "Installing backend dependencies..." -ForegroundColor Green
        Set-Location backend
        pip install -r requirements.txt
        Set-Location ..
        
        Write-Host "Installing frontend dependencies..." -ForegroundColor Green
        Set-Location frontend
        npm install
        Set-Location ..
        
        Write-Host "Dependencies installed successfully!" -ForegroundColor Green
    }
    "run" {
        Write-Host "Starting Multi-Bot RAG Platform..." -ForegroundColor Green
        docker-compose up --build
    }
    "stop" {
        Write-Host "Stopping application..." -ForegroundColor Yellow
        docker-compose down
    }
    "logs" {
        docker-compose logs -f
    }
    "clean" {
        Write-Host "Cleaning up containers and volumes..." -ForegroundColor Red
        docker-compose down -v
        docker system prune -f
    }
    default {
        Write-Host "Usage: .\run.ps1 [install|run|stop|logs|clean]" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor White
        Write-Host "  install  - Install all dependencies" -ForegroundColor Gray
        Write-Host "  run      - Start the entire application" -ForegroundColor Gray
        Write-Host "  stop     - Stop the application" -ForegroundColor Gray
        Write-Host "  logs     - View logs" -ForegroundColor Gray
        Write-Host "  clean    - Clean up containers and volumes" -ForegroundColor Gray
    }
}