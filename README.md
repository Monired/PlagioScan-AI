# PlagioScan AI

AI-powered academic plagiarism and originality analysis system built with Python and Flask.

## Overview

PlagioScan AI is a web-based application that analyzes academic documents to identify potentially matching content and provide originality insights.

## Key Features

- Document text extraction
- Plagiarism and similarity detection
- TF-IDF and Cosine Similarity analysis
- N-Gram similarity analysis
- Jaccard similarity analysis
- Fuzzy text matching
- Web-source comparison
- Writing-style analysis
- Originality analysis
- Research-depth analysis
- Grammar analysis
- Citation checking
- Document comparison
- Analysis dashboard
- PDF report generation
- User authentication and profile management
- REST API
- Automated testing

## Technologies

- Python
- Flask
- Scikit-learn
- SQLite
- HTML
- CSS
- JavaScript

## How It Works

1. The user uploads an academic document.
2. The application extracts and processes the document text.
3. Multiple similarity techniques are used to analyze potentially matching content.
4. TF-IDF and Cosine Similarity are used for textual similarity analysis.
5. The system can compare content with available web sources.
6. Writing and originality analysis is performed.
7. Results are displayed through the web dashboard.
8. Reports can be generated from the analysis results.

## Project Structure

```text
PlagioScan-AI/
│
├── models/
├── routes/
├── services/
├── static/
├── templates/
├── tests/
├── utils/
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
└── run.py

## Installation & Setup
1. Clone the Repository
git clone https://github.com/Monired/PlagioScan-AI.git
cd PlagioScan-AI
2. Create a Virtual Environment
python -m venv venv
3. Activate the Virtual Environment
Windows
venv\Scripts\activate
macOS/Linux
source venv/bin/activate
4. Install Dependencies

Install all required Python packages using the project's requirements file:

pip install -r requirements.txt
5. Run the Application

Start the Flask application using:

python run.py

After the application starts, open:

http://127.0.0.1:5000
6. Run Tests

To run the automated tests:

pytest

For detailed test output:

pytest -v
Security

The application includes security-related features such as:

CSRF protection
Password hashing
Input validation
Secure file handling
Session security
Database operations using SQLAlchemy
Future Improvements
Improved semantic similarity
Enhanced document comparison
Improved source verification
Additional language support
Enhanced reporting
Cloud deployment
