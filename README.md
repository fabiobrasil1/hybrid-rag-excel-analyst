📊 Hybrid RAG Excel Analyst

Hybrid RAG system for Excel analytics that enables natural language queries, precise calculations, and actionable insights.

This project combines Retrieval-Augmented Generation (RAG) with structured data querying (pandas/SQL) to go beyond traditional document-based RAG systems, enabling real analytical reasoning over spreadsheet data.

🚀 Overview

Working with spreadsheets often requires manual filtering, calculations, and exploration.

This system allows you to:

Ask questions in natural language
Perform real calculations on data
Extract insights automatically
Analyze spreadsheets without writing code
💡 Example Queries

You can ask questions like:

“What is the average revenue per region?”
“Which product had the highest sales last month?”
“Show the top 5 customers by total spending”
“Is there any downward trend in the last quarter?”
“Compare performance between regions”
“Give me 5 insights from this dataset”
🧠 How It Works

This is not a traditional RAG system. It uses a hybrid architecture:

1. Data Ingestion
Reads Excel files (.xlsx, .csv)
Supports multiple sheets
Extracts schema and metadata
2. Schema Understanding
Detects:
column types (numeric, categorical, datetime)
relationships
potential metrics
3. Hybrid RAG Layer
Uses embeddings to retrieve:
column descriptions
metadata
business context
Helps the model understand what the data means
4. Structured Query Engine
Converts natural language → executable queries
Executes using:
pandas or SQL (DuckDB)
Supports:
aggregations
filtering
grouping
sorting
5. Insight Generation
Computes real statistics
Detects:
trends
outliers
patterns
Uses LLM to generate explanations
⚙️ Tech Stack
Language Model: GPT / Claude / Llama
Data Processing: pandas
Query Engine: DuckDB / SQL
Embeddings: OpenAI / sentence-transformers
Vector Store: FAISS / Qdrant / pgvector
Backend: Python / FastAPI
Frontend (optional): Streamlit / React
🧩 Key Features
Hybrid RAG + structured querying
Natural language interface for spreadsheets
Real data calculations (not just text retrieval)
Schema-aware reasoning
Insight generation from structured data
Supports multiple spreadsheet formats
🔍 Why Hybrid RAG?

Traditional RAG systems:

Retrieve text
Generate answers

This system:

Retrieves context AND
Executes real computations

👉 This avoids hallucinations and produces accurate, data-driven answers.

📁 Project Structure (example)
hybrid-rag-excel-analyst/
│
├── data/                # Sample spreadsheets
├── embeddings/         # Vector storage
├── src/
│   ├── ingestion/      # Excel/CSV loaders
│   ├── schema/         # Data understanding
│   ├── rag/            # Retrieval logic
│   ├── query_engine/   # pandas / SQL execution
│   ├── insights/       # Insight generation
│   └── api/            # FastAPI endpoints
│
├── notebooks/          # Experiments
├── app.py              # Entry point
├── requirements.txt
└── README.md
▶️ Getting Started
1. Clone the repository
git clone https://github.com/your-username/hybrid-rag-excel-analyst.git
cd hybrid-rag-excel-analyst
2. Install dependencies
pip install -r requirements.txt
3. Run the application
python app.py
📊 Example Workflow
Upload an Excel file
System reads and understands schema
User asks a question
System:
retrieves context (RAG)
generates query
executes calculation
Returns:
answer
explanation
insights
📈 Future Improvements
 Visualization (charts & dashboards)
 Multi-file analysis
 Time-series forecasting
 Advanced anomaly detection
 Integration with BI tools
 Support for databases (Postgres, BigQuery)
🎯 Use Cases
Business analytics
Financial analysis
Sales performance tracking
Customer segmentation
Operational reporting
Self-service data analysis
🧪 Challenges Addressed
Bridging unstructured + structured data
Avoiding LLM hallucinations in numeric tasks
Translating natural language into precise queries
Maintaining explainability in AI-generated insights
🤝 Contributing

Contributions are welcome. Feel free to open issues or submit pull requests.

📄 License

MIT License

⭐ Final Note

This project demonstrates how combining RAG + structured data analytics enables a new class of intelligent systems capable of both understanding context and performing real computations.
