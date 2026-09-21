#Reatail Platform
Enterprise Reatail Platform deployment project.
## Appliction

- Application: Retail Platform 
- Version: 4.3.0
- Port: 8081
- Technology: Python Flask
- Containerization: Docker
## Health Check
The application provides:
- `/` - Applcation information
-`/health` - Application health status
## Git Branches
- main - Production 
- develop - Development
- release/4.3.0 - Release preparation
- hotfix/payment-4.2.1 - Emergency payment  fix
## Docker 
Build the application:
docker compose build
Run the application:
docker compose up
the application will be available on port 8081.