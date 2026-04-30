# Whistleblower Ethics Hotline

A platform for secure reporting of ethical violations and complaints.

## 📋 Project Overview

- **Backend**: Java Spring Boot with JWT authentication
- **Frontend**: React (in development)
- **AI Service**: Python Flask (in development)
- **Database**: MySQL

---

## ✅ Implemented Features

### Backend

#### Authentication

- ✅ JWT Token generation and validation
- ✅ Login endpoint: `POST /auth/login` (test: admin/1234)
- ✅ JWT Auth Filter for protecting routes

#### Complaints API

- ✅ `POST /api/complaints/create` - Create new complaint (sends email notification)
- ✅ `GET /api/complaints/all?page=0&size=5` - List all complaints (paginated)
- ✅ `GET /api/complaints/{id}` - Get complaint by ID
- ✅ `PUT /api/complaints/{id}` - Update complaint (sends status update email)
- ✅ `DELETE /api/complaints/{id}` - Delete complaint
- ✅ Query: `GET /api/complaints/search` - Find by status or keyword (repository support)

#### Email Notifications

- ✅ JavaMailSender integration for sending emails
- ✅ Thymeleaf HTML email templates:
  - ✅ Complaint created notification
  - ✅ Daily reminder (9:00 AM)
  - ✅ Deadline alerts (every 6 hours)
  - ✅ Status update notifications

#### Scheduled Tasks

- ✅ `@Scheduled` daily reminder at 9:00 AM
- ✅ `@Scheduled` deadline alert check every 6 hours
- ✅ `@Scheduled` hourly status monitoring

#### Security & Caching

- ✅ Redis caching with 10 min TTL on GET endpoints
- ✅ @CacheEvict on write operations (create, update, delete)
- ✅ RBAC with @PreAuthorize annotations:
  - ✅ ROLE_USER - Can create and view complaints
  - ✅ ROLE_ADMIN - Can update, delete, and manage all complaints
  - ✅ JWT roles embedded in tokens

#### Error Handling & Testing

- ✅ @ControllerAdvice for centralized exception handling
- ✅ Consistent JSON error responses (ApiError DTO):
  - ✅ 404 Not Found (ComplaintNotFoundException)
  - ✅ 400 Bad Request (validation errors)
  - ✅ 500 Internal Server Error (generic exceptions)
- ✅ JUnit 5 unit tests with Mockito:
  - ✅ ComplaintServiceTest (4 test cases)
  - ✅ EmailServiceTest (2 test cases)
  - ✅ WhistleblowerApplicationTests (context loading)
  - ✅ 7 total tests passing ✅

#### Additional Features

- ✅ Global exception handling
- ✅ Input validation with @Valid annotations
- ✅ Complaint status tracking (OPEN status on creation)

### Data Models

- ✅ Complaint Entity (id, title, description, status, createdAt, updatedAt)
- ✅ AppUser Entity (id, username, password)

---

## 🚧 TODO / In Development

- [x] **Day 7: Email Notifications** - Completed ✅
  - [x] JavaMailSender integration
  - [x] Thymeleaf HTML templates
  - [x] @Scheduled daily reminders
  - [x] Deadline alerts
- [x] **Day 8: Error Handling & Unit Tests** - Completed ✅
  - [x] @ControllerAdvice for consistent error responses
  - [x] JUnit 5 unit tests with Mockito
  - [x] Test coverage: 7 passing tests
- [x] **Day 9: Docker & Containerization** - Completed ✅
  - [x] Multi-stage Docker build for Backend (Java)
  - [x] Docker build for Frontend (React + Nginx)
  - [x] Docker build for AI Service (Python Flask)
  - [x] PostgreSQL container with volume persistence
  - [x] Redis container with volume persistence
  - [x] Docker Compose orchestration (all 5 services)
  - [x] Health checks for all services
  - [x] Test scripts (docker-test.sh and docker-test.ps1)
- [ ] User registration: `POST /auth/register`
- [ ] User logout: `POST /auth/logout`
- [ ] Frontend UI improvements
- [ ] Database migrations setup
- [ ] Password hashing/encryption

---

## 🚀 Quick Start

### Backend

```bash
cd backend
./mvnw clean install
./mvnw spring-boot:run
```

API runs on: http://localhost:8080

**Test Login:**

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"1234"}'
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Docker

**One-command full stack deployment:**

```bash
docker-compose up --build
```

**Services Started:**

1. 🗄️ **PostgreSQL** - Port 5432
2. 💾 **Redis** - Port 6379
3. 🔧 **Backend** - Port 8080
4. 🤖 **AI Service** - Port 5000
5. 🌐 **Frontend** - Port 3000

**Test all services with health checks:**

```bash
# PowerShell (Windows)
.\docker-test.ps1

# Bash (Linux/Mac)
bash docker-test.sh
```

**Verify services are running:**

```bash
# Check all container status
docker-compose ps

# View backend logs
docker-compose logs -f backend

# Check AI service health
curl http://localhost:5000/health

# Check backend health
curl http://localhost:8080/auth/health
```

**Stop and cleanup:**

```bash
# Stop all services
docker-compose down

# Remove all data volumes
docker-compose down -v

# Restart services
docker-compose restart
```

**Docker Architecture:**

```
┌─────────────────────────────────────────────────┐
│           Docker Network Bridge                 │
├──────────┬──────────┬──────────┬──────────┬─────┤
│PostgreSQL│  Redis   │ Backend  │    AI    │ FE  │
│  :5432   │  :6379   │  :8080   │  :5000   │:3000│
└──────────┴──────────┴──────────┴──────────┴─────┘
```

**Dockerfile Specs:**

- **Backend**: Multi-stage build (Maven compile → Java 17 runtime)
- **Frontend**: Multi-stage build (Node build → Nginx runtime)
- **AI Service**: Python 3.11 slim with Flask
- All services include health checks

---

## � Email Configuration

### Setup Gmail for sending emails:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Select App: Mail, Device: Windows/Mac/Linux
   - Copy the generated password

3. **Update `application.yml`:**
   ```yaml
   spring:
     mail:
       host: smtp.gmail.com
       port: 587
       username: your-email@gmail.com
       password: your-16-char-app-password
   ```

### Email Templates:

- `complaint-created.html` - Sent when complaint is created
- `daily-reminder.html` - Sent daily at 9:00 AM
- `deadline-alert.html` - Sent every 6 hours if deadline approaching
- `status-update.html` - Sent when complaint status changes

### Scheduled Tasks:

- **Daily Reminder**: Runs at 9:00 AM every day
- **Deadline Alert**: Runs every 6 hours (0:00, 6:00, 12:00, 18:00 UTC)
- **Hourly Status Check**: Runs every hour

---

## 🧪 Testing

### Run Unit Tests

```bash
cd backend
./mvnw test
```

**Test Coverage:**

- **ComplaintServiceTest** (4 tests)
  - `testGetAllComplaints_Success` - Retrieve all complaints
  - `testGetAllPaginated_Success` - Paginated retrieval
  - `testGetById_Success` - Get single complaint by ID
  - `testGetById_NotFound` - 404 exception handling

- **EmailServiceTest** (2 tests)
  - `testSendSimpleEmail_Success` - Plain text email sending
  - `testSendSimpleEmail_Error` - Error handling and graceful degradation

- **WhistleblowerApplicationTests** (1 test)
  - Application context loads successfully

**Test Framework:** JUnit 5 (Jupiter) with Mockito mocking

---

## 🔐 Login Credentials

**Admin Account (Full Access):**

- Username: `admin`
- Password: `admin123` (or legacy: `1234`)
- Roles: ROLE_ADMIN, ROLE_USER

**Regular User (View/Create):**

- Username: `user`
- Password: `user123`
- Roles: ROLE_USER

---

## 📝 Notes for Development

- JWT Secret: Currently hardcoded (move to config)
- Email: Configure Gmail app password in `application.yml`
- Database: PostgreSQL running on localhost:5432
- Redis: Required for caching (localhost:6379)
- Test credentials: Update before production
- Email recipients: Currently hardcoded to `admin@whistleblower.com` (update in code)

---

**Last Updated:** April 27, 2026
**Day 7 Completion:** Email Notifications, Scheduled Tasks, RBAC, Redis Caching
