# FastAPI + Gemini Backend

This project is a beginner-friendly backend that:

- uploads PDF or DOCX files
- extracts the text
- stores the extracted text temporarily in memory
- sends the document text and user question to Gemini
- returns an answer based only on the document
- can also generate a short structured summary

## 1. Project files

- `main.py` -> your FastAPI backend
- `requirements.txt` -> Python libraries to install
- `.env.example` -> where to place your Gemini API key

## 2. Create a virtual environment

Open terminal in this project folder and run:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

If you are on Windows, use:

```bash
venv\Scripts\activate
```

## 3. Install libraries

```bash
pip install -r requirements.txt
```

## 4. Add your Gemini API key

Create a file named `.env` in the same folder as `main.py`.

Copy this into the `.env` file:

```env
GEMINI_API_KEY=PASTE_YOUR_REAL_GEMINI_API_KEY_HERE
GEMINI_MODEL=gemini-2.0-flash
CORS_ORIGINS=*
```

Important:

- Replace `PASTE_YOUR_REAL_GEMINI_API_KEY_HERE` with your real Gemini API key.
- `CORS_ORIGINS=*` allows any frontend to connect. This is fine for learning.
- Later, for better security, you can replace `*` with your website URL.

Example:

```env
CORS_ORIGINS=http://localhost:3000
```

Or multiple websites:

```env
CORS_ORIGINS=http://localhost:3000,https://yourwebsite.com
```

## 5. Run the backend

```bash
uvicorn main:app --reload
```

When it starts, open:

- API home: `http://127.0.0.1:8000`
- Swagger test page: `http://127.0.0.1:8000/docs`

## 6. How the backend works

### `/upload`

Use this endpoint to upload a PDF or DOCX file.

What it does:

1. saves the file temporarily in the `temp_uploads` folder
2. reads the text from the file
3. stores the text in memory using a `document_id`
4. returns the `document_id` to your frontend

You need this `document_id` later when asking questions.

### `/ask`

Use this endpoint to ask a question about the uploaded document.

You send:

```json
{
  "document_id": "your-document-id",
  "question": "What are the mission objectives?"
}
```

The backend:

1. finds the stored document text
2. combines the document text + user question into a prompt
3. sends the prompt to Gemini
4. tells Gemini to answer only from the document
5. returns the answer as JSON

### `/summary`

This is the bonus endpoint.

You send:

```json
{
  "document_id": "your-document-id"
}
```

The backend returns a short structured report summary.

## 7. How to test the backend

### Option A: easiest way using browser

Open:

```text
http://127.0.0.1:8000/docs
```

Then:

1. click `POST /upload`
2. click `Try it out`
3. choose a PDF or DOCX file
4. click `Execute`
5. copy the returned `document_id`
6. open `POST /ask`
7. click `Try it out`
8. paste the `document_id`
9. type a question
10. click `Execute`

You can also test `POST /summary` the same way.

### Option B: test using curl

Upload a file:

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/full/path/to/your/file.pdf"
```

Ask a question:

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "PASTE_DOCUMENT_ID_HERE",
    "question": "What sensors were used?"
  }'
```

Generate a summary:

```bash
curl -X POST "http://127.0.0.1:8000/summary" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "PASTE_DOCUMENT_ID_HERE"
  }'
```

## 8. How to connect it to your website frontend

Your frontend should do this in 2 steps:

### Step 1: upload the file

Example JavaScript:

```html
<input type="file" id="fileInput" />
<button onclick="uploadFile()">Upload</button>

<script>
  let currentDocumentId = "";

  async function uploadFile() {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    if (!file) {
      alert("Please choose a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    currentDocumentId = data.document_id;
    console.log("Upload result:", data);
    alert("File uploaded successfully.");
  }
</script>
```

### Step 2: ask a question

```html
<input type="text" id="questionInput" placeholder="Ask a question" />
<button onclick="askQuestion()">Ask</button>

<script>
  async function askQuestion() {
    const question = document.getElementById("questionInput").value;

    if (!currentDocumentId) {
      alert("Upload a file first.");
      return;
    }

    const response = await fetch("http://127.0.0.1:8000/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        document_id: currentDocumentId,
        question: question
      })
    });

    const data = await response.json();
    console.log("Answer:", data);
    alert(data.answer);
  }
</script>
```

### Optional Step 3: generate summary

```javascript
async function generateSummary() {
  if (!currentDocumentId) {
    alert("Upload a file first.");
    return;
  }

  const response = await fetch("http://127.0.0.1:8000/summary", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      document_id: currentDocumentId
    })
  });

  const data = await response.json();
  console.log("Summary:", data.summary);
}
```

## 9. Important beginner notes

- The extracted document text is stored temporarily in memory.
- If you stop the backend server, the stored text will be lost.
- If you want permanent storage later, you can add a database.
- Very large files may need chunking or a database in a future version.
- For a final year project, this version is a good simple starting point.

## 10. What to do next

Suggested order:

1. run the backend
2. test it in `/docs`
3. connect your website upload form
4. connect your website question form
5. improve the UI after the backend works
