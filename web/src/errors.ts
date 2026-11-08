import { ApiError } from "./api";

// A friendly sentence for anything that can go wrong when talking to the server. It never shows
// internal codes, status numbers or exception text.
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Please sign in as a demo member first.";
    if (error.status === 400 && error.code === "unknown_store") return "I don't recognise this store page.";
    if (error.status === 422) return "That message can't be sent. Please keep it between 1 and 2000 characters.";
    if (error.status === 503) return "The assistant is not set up on this server yet.";
    if (error.status === 502) return "The assistant is temporarily unavailable. Please try again in a moment.";
    if (error.status === 0) return "Can't reach the server. Check your connection and try again.";
  }
  return "Something went wrong. Please try again.";
}
