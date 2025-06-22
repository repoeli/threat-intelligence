# 🛡️ Threat Intelligence Platform

A comprehensive threat intelligence analysis platform with modern web interface, built with FastAPI backend and React TypeScript frontend.

## ✨ Features

### 🔐 Authentication System
- JWT-based user authentication
- Secure registration and login
- Protected routes and session management
- User database with password hashing

### 📊 Threat Analysis
- Multi-source threat intelligence analysis
- Support for IPs, domains, URLs, and file hashes
- VirusTotal API integration
- Real-time threat scoring and risk assessment
- Vendor results aggregation
- Geolocation and timeline data
- Analysis history storage

### 🎨 Modern UI
- Responsive React TypeScript frontend
- Tailwind CSS styling
- Real-time analysis results
- Professional dashboard interface
- Mobile-friendly design

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file with your API keys
VIRUSTOTAL_API_KEY=your_vt_key_here
JWT_SECRET_KEY=your_secret_key_here

# Start backend
python ../start_server.py
```

### Initialize Database
Run the migration script once to create the SQLite database and seed a default admin user.

```bash
python migrate_to_db.py
```

Set `DATABASE_URL` in `.env` before running the script if you want to use PostgreSQL.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker Setup (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or with standalone Docker
docker build -t threat-intel:latest .
docker run -d --name threat-intel -p 8686:8686 --env-file backend/.env threat-intel:latest
```

## 📖 API Documentation
- Frontend Application: http://localhost:3001
- Backend API: http://localhost:8686
- FastAPI Interactive Docs: http://localhost:8686/docs
- ReDoc Documentation: http://localhost:8686/redoc

## 🔧 Configuration

### Environment Variables
```bash
# Required
VIRUSTOTAL_API_KEY=your_virustotal_api_key
JWT_SECRET_KEY=your_jwt_secret_key

# Optional
ABUSEIPDB_API_KEY=your_abuseipdb_key
OPENAI_API_KEY=your_openai_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## 🏗️ Architecture

### Backend (FastAPI)
- **Authentication**: JWT tokens, password hashing, user management
- **Analysis Engine**: Multi-source threat intelligence aggregation
- **Database**: SQLAlchemy with SQLite/PostgreSQL support
- **APIs**: RESTful endpoints with OpenAPI documentation

### Frontend (React + TypeScript)
- **State Management**: React Query for server state
- **Routing**: React Router with protected routes
- **Styling**: Tailwind CSS for responsive design
- **Forms**: Controlled components with validation

## 📁 Project Structure
```
threat-intelligence/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── services/       # Business logic
│   │   ├── clients/        # External API clients
│   │   ├── utils/          # Utilities
│   │   └── ...
│   └── requirements.txt
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API clients
│   │   └── ...
│   └── package.json
├── tests/                  # Test suites
├── docker-compose.yml      # Docker configuration
└── README.md
```

## 🧪 Testing

```bash
# Run backend tests
pytest tests/

# Run frontend tests (when available)
cd frontend && npm test
```

## 🔒 Security Features

- JWT token-based authentication
- Password hashing with bcrypt
- Protected API endpoints
- Input validation and sanitization
- CORS configuration
- Environment-based secrets management

## 📊 Current Status

✅ **Completed Features**:
- User authentication (register, login, logout)
- JWT token management
- Database integration with SQLAlchemy
- VirusTotal API integration
- Comprehensive threat analysis
- Modern React frontend with Tailwind CSS
- Analysis results visualization
- Vendor results display
- Docker containerization

🚧 **Planned Features**:
- Analysis history dashboard
- Bulk analysis capabilities
- Advanced filtering and search
- Real-time notifications
- Export functionality
- Admin panel

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions, please use the GitHub Issues page or contact the maintainers.
