# Beca 18 RAG Chatbot

This project builds a Retrieval-Augmented Generation pipeline for the official Beca 18 regulation:

`Resolucion Directoral Ejecutiva N. 033-2026-MINEDU/VMGI-PRONABEC`

Source page: https://www.gob.pe/institucion/pronabec/normas-legales/7778068-033-2026-minedu-vmgi-pronabec

## Pipeline summary

The notebook extracts text from the PDF page by page, adds page markers, cleans the text, splits it into overlapping chunks, embeds those chunks with Gemini embeddings, stores them in a persistent ChromaDB collection, retrieves relevant chunks for each question, and asks Gemini 2.5 Flash to answer only from the retrieved context with page citations.

## Installation

```powershell
python -m pip install -r requirements.txt
```

## API key setup

Create a local `.env` file from `.env.example`:

```text
GEMINI_API_KEY=your_key_here
```

Do not commit `.env`.

## Run

Open and run all cells in:

```text
notebooks/beca18_rag_chatbot.ipynb
```

The notebook is idempotent: if `chroma_db_beca18/` already contains indexed chunks, it loads the existing collection instead of embedding the PDF again.

## Chat interface

At the end of the notebook, use the text input to ask a question, adjust the `k` slider to control the number of retrieved chunks, and inspect the expandable source fragments with page numbers and distances.
