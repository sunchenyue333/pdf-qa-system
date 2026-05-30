"use client";

import axios from "axios";
import { useRef, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

interface UploadResponse {
  message?: string;
  pages?: number;
  [key: string]: unknown;
}

interface AskRequest {
  question: string;
}

interface AskResponse {
  answer: string;
  sources: number[];
}

interface ChatItem {
  question: string;
  answer: string;
  sources: number[];
}

function formatUploadResult(data: UploadResponse): string {
  if (data.message) return data.message;
  if (typeof data.pages === "number") {
    return `Processed ${data.pages} page(s)`;
  }
  return JSON.stringify(data);
}

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [pdfReady, setPdfReady] = useState(false);

  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatItem[]>([]);

  const loading = uploading || asking;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);
    setFileName(file.name);
    setUploadResult(null);
    setPdfReady(false);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const { data } = await axios.post<UploadResponse>(
        `${API_BASE}/upload`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setUploadResult(formatUploadResult(data));
      setPdfReady(true);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data as { detail?: string })?.detail ??
          err.message
        : "Upload failed";
      setError(String(msg));
      setFileName(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    if (!pdfReady) {
      setError("Please upload a PDF first");
      return;
    }

    setError(null);
    setAsking(true);

    const body: AskRequest = { question: trimmed };

    try {
      const { data } = await axios.post<AskResponse>(
        `${API_BASE}/ask`,
        body
      );
      setHistory((prev) => [
        ...prev,
        {
          question: trimmed,
          answer: data.answer,
          sources: data.sources,
        },
      ]);
      setQuestion("");
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data as { detail?: string })?.detail ??
          err.message
        : "Failed to get an answer";
      setError(String(msg));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 px-4 py-10 font-sans dark:bg-zinc-950">
      <main className="mx-auto flex w-full max-w-[800px] flex-col gap-8">
        <header>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            PDF Q&A
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Upload a PDF, then ask questions about its content
          </p>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300"
          >
            {error}
          </div>
        )}

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Upload PDF
          </h2>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            className="flex min-h-[120px] w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-zinc-300 bg-white px-6 py-8 text-center transition-colors hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-500 dark:hover:bg-zinc-800/80"
          >
            {uploading ? (
              <span className="text-sm text-zinc-500">Uploading and processing…</span>
            ) : (
              <>
                <span className="text-zinc-600 dark:text-zinc-400">
                  Click to select a PDF file
                </span>
                <span className="text-xs text-zinc-400">.pdf only</span>
              </>
            )}
          </button>
          {fileName && (
            <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm dark:border-zinc-800 dark:bg-zinc-900">
              <p className="font-medium text-zinc-800 dark:text-zinc-200">
                File: {fileName}
              </p>
              {uploadResult && (
                <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                  Result: {uploadResult}
                </p>
              )}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Ask a question
          </h2>
          <form onSubmit={handleAsk} className="flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter your question…"
              disabled={loading || !pdfReady}
              className="flex-1 rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-sm text-zinc-900 outline-none ring-zinc-400 focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
            />
            <button
              type="submit"
              disabled={loading || !pdfReady || !question.trim()}
              className="rounded-lg bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {asking ? "Submitting…" : "Submit"}
            </button>
          </form>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Chat history
          </h2>
          {history.length === 0 ? (
            <p className="text-sm text-zinc-400">No messages yet</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {history.map((item, index) => (
                <li
                  key={index}
                  className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
                >
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                    Question
                  </p>
                  <p className="mt-1 text-zinc-900 dark:text-zinc-100">
                    {item.question}
                  </p>
                  <p className="mt-4 text-sm font-medium text-zinc-500 dark:text-zinc-400">
                    Answer
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-zinc-800 dark:text-zinc-200">
                    {item.answer}
                  </p>
                  {item.sources.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {item.sources.map((page) => (
                        <span
                          key={page}
                          className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                        >
                          Page {page}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
