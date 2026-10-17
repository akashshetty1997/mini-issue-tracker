"use client";

import { useState } from "react";

import { useDebouncedCallback } from "@/hooks/useDebouncedCallback";
import { SEARCH_DEBOUNCE_MS } from "@/lib/constants";

interface SearchInputProps {
  value: string;
  onSearch: (value: string) => void;
}

/** Text input that reports its value after the user pauses typing (or presses Enter). */
export function SearchInput({ value, onSearch }: SearchInputProps) {
  const [text, setText] = useState(value);
  const [syncedValue, setSyncedValue] = useState(value);
  const debouncedSearch = useDebouncedCallback(onSearch, SEARCH_DEBOUNCE_MS);

  // Follow external changes (e.g. "Clear filters" or browser back) without an effect.
  if (value !== syncedValue) {
    setSyncedValue(value);
    setText(value);
  }

  return (
    <input
      type="search"
      value={text}
      placeholder="Search title or description…"
      aria-label="Search issues"
      onChange={(event) => {
        setText(event.target.value);
        debouncedSearch(event.target.value.trim());
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") onSearch(text.trim());
      }}
      className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
    />
  );
}
