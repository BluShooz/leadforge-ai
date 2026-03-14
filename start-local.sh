#!/bin/bash

# LeadForge AI - Local Start Script

echo "🚀 Starting LeadForge AI (Local Mode)"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "📥 Installing backend dependencies..."
cd backend
pip install -q fastapi uvicorn sqlalchemy pydantic pydantic-settings python-jose passlib bcrypt python-multipart
pip install -q httpx aiohttp celery redis beautifulsoup4 lxml
cd ..

# Create local .env
if [ ! -f ".env.local" ]; then
    echo "📝 Creating local environment..."
    cat > .env.local << EOF
DATABASE_URL=sqlite:///./leadforge.db
SECRET_KEY=local-dev-secret-key-change-in-production
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
ENVIRONMENT=development
DEBUG=true
EOF
fi

# Start backend in background
echo "🔧 Starting backend server..."
cd backend
DATABASE_URL=sqlite:///./leadforge.db uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "⏳ Waiting for backend to start..."
sleep 5

# Install frontend dependencies
echo "📥 Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi

# Create frontend .env
if [ ! -f ".env.local" ]; then
    echo "📝 Creating frontend environment..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
fi

# Start frontend
echo "🎨 Starting frontend server..."
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ LeadForge AI is starting!"
echo ""
echo "📍 Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop this monitoring script (servers will keep running)"

# Monitor processes
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
