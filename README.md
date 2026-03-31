# abtestingapp
This app helps for ui/ux designers to present their screens and take feedback in the form of a simple option to reason questionnaire format and get results with insights.

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
API runs at http://localhost:8000

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at http://localhost:3000

### Tests
```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```
