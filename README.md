# 📋 FastAPI CRUD Todo Application

A modern, production-ready CRUD API built with FastAPI, PostgreSQL, Docker, and Alembic migrations. This project demonstrates best practices for building scalable web APIs with automatic database migrations.

## ✨ Features

- 🚀 **FastAPI** - Modern, fast web framework for APIs
- 🐘 **PostgreSQL** - Robust relational database
- 🐳 **Docker** - Containerized application
- 🔄 **Alembic** - Database migrations
- 🔍 **UUID** - Secure primary keys
- ⚡ **UV** - Super-fast Python package manager
- 📚 **Automatic Documentation** - Interactive API docs
- 🛡️ **Input Validation** - Pydantic schemas
- 🏗️ **Clean Architecture** - Separation of concerns
- ⏰ **Automatic Timestamps** - Created/updated tracking

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.13
- **Database:** PostgreSQL 15
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Package Manager:** UV
- **Containerization:** Docker & Docker Compose
- **Validation:** Pydantic

## 📋 Prerequisites

### For Docker (Recommended)
- Docker & Docker Compose

### For Local Development (Optional)
- Python 3.12+
- UV package manager

## 🚀 Quick Start

### Option 1: Docker (Recommended)

#### 1. Clone the repository
```bash
git clone https://github.com/diegoddie/fastapi-docker-boilerplate.git
cd fastapi-crud
```

#### 2. Create environment file
Create `.env` at the project root with your configuration:
```env
POSTGRES_DB=fastapi_db
POSTGRES_USER=fastapi_user
POSTGRES_PASSWORD=fastapi_password
DATABASE_URL=postgresql://fastapi_user:fastapi_password@db:5432/fastapi_db
```

#### 3. Start the application
```bash
docker-compose up --build
```

#### 4. Create database migrations
```bash
docker-compose exec api uv run alembic revision --autogenerate -m "Create todos table"
```

#### 5. Apply database migrations
```bash
docker-compose exec api uv run alembic upgrade head
```

#### 6. Testing
Access the interactive API documentation at:
- http://localhost:8000/docs

Use the built-in interface to test all endpoints with real data.

### Option 2: Local Development

#### 1. Clone the repository
```bash
git clone https://github.com/diegoddie/fastapi-docker-boilerplate.git
cd fastapi-crud
```

#### 2. Install UV
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 3. Install dependencies
```bash
uv sync
```

#### 4. Set up local PostgreSQL
Make sure you have PostgreSQL running locally, then create `.env`:
```env
POSTGRES_DB=fastapi_db
POSTGRES_USER=your_local_user
POSTGRES_PASSWORD=your_local_password
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/fastapi_db
```

#### 5. Create database migrations
```bash
uv run alembic revision --autogenerate -m "Create todos table"
```

#### 6. Apply database migrations
```bash
uv run alembic upgrade head
```

#### 7. Start the application
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 8. Testing
Access the interactive API documentation at:
- http://localhost:8000/docs

## 🧪 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/todos/` | Get all todos |
| `GET` | `/api/todos/{todo_id}` | Get a specific todo |
| `POST` | `/api/todos/` | Create a new todo |
| `PUT` | `/api/todos/{todo_id}` | Update a todo |
| `DELETE` | `/api/todos/{todo_id}` | Delete a todo |

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- SQLAlchemy team for the excellent ORM
- Alembic team for database migrations
- Docker team for containerization

## 📞 Support

If you found this project helpful:
- ⭐ Star the repository
- 🐛 Report bugs via issues
- 💡 Submit feature requests
- 📺 Subscribe to the YouTube channel

---

**Built with ❤️ for the dev community**
