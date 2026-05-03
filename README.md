This project is a backend system designed to securely manage and track complaints. It is built using Spring Boot, PostgreSQL, and Docker, with support for authentication, validation, and testing. The system provides REST APIs for complaint management and demonstrates real-world backend development practices.

Tech Stack

Backend: Spring Boot (Java 17)
Database: PostgreSQL
Authentication: JWT (JSON Web Token)
Containerization: Docker and Docker Compose
Build Tool: Maven
Testing: Spring Boot Test, MockMvc

Features
User authentication using JWT
Create complaint
View complaints with pagination
Update complaint
Delete complaint
Input validation
Global exception handling
Dockerized application setup
Basic unit and controller testing
Project Structure

src/
controller/
service/
repository/
entity/
config/
exception/
security/

Development Progress
Day 1–2: Project Setup
Initialized Spring Boot project
Configured Maven dependencies
Set up project structure
Connected PostgreSQL database
Day 3–4: Backend Development
Created entities: AppUser and Complaint
Implemented JPA repositories
Developed service layer
Built REST APIs for complaint management
Day 5: Authentication
Implemented JWT authentication
Secured endpoints using Spring Security
Added login functionality
Day 6–7: Enhancements
Added validation using annotations
Implemented global exception handling
Added pagination support
Configured email service
Day 8: Redis Integration (Removed Later)
Integrated Redis caching
Encountered serialization issues
Removed Redis to maintain system stability
Day 9: Dockerization
Created Dockerfile for backend
Created docker-compose configuration
Added PostgreSQL and Redis services
Added health checks
Successfully ran services using Docker
Day 10: Integration Testing
Performed clean Docker rebuild
Tested all APIs using Postman
Fixed serialization issues
Fixed caching-related errors
Improved exception handling
Day 11: Final Testing and Stability
Verified all API endpoints
Added unit and controller tests
Ensured application stability
Improved error handling and logging
API Endpoints

Authentication

POST /auth/login

Complaints

POST /api/complaints/create
GET /api/complaints
GET /api/complaints/{id}
PUT /api/complaints/{id}
DELETE /api/complaints/{id}

Running the Application

Build and run using Docker:

docker-compose up --build

Stop the application:

docker-compose down -v