"use client";

import { useState } from "react";

interface PasswordFieldProps {
  label: string;
  name: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
}

const INPUT_CLASS_NAME =
  "w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 pr-10 " +
  "text-slate-100 outline-none focus:border-sky-500";

export function PasswordField({
  label,
  name,
  autoComplete,
  value,
  onChange,
}: PasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const toggleLabel = isVisible ? "Ukryj hasło" : "Pokaż hasło";

  return (
    <label className="flex flex-col gap-1.5 text-sm text-slate-300">
      {label}
      <span className="relative">
        <input
          type={isVisible ? "text" : "password"}
          name={name}
          autoComplete={autoComplete}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required
          className={INPUT_CLASS_NAME}
        />
        <button
          type="button"
          onClick={() => setIsVisible((current) => !current)}
          className={
            "absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 " +
            "text-slate-400 hover:text-slate-200"
          }
          aria-label={toggleLabel}
          aria-pressed={isVisible}
          title={toggleLabel}
        >
          {isVisible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </span>
    </label>
  );
}

function EyeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M2.06 12.32a1 1 0 0 1 0-.64C3.42 7.51 7.36 4.5 12 4.5s8.58 3.01 9.94 7.18a1 1 0 0 1 0 .64C20.58 16.49 16.64 19.5 12 19.5S3.42 16.49 2.06 12.32Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M3.98 8.22A10.48 10.48 0 0 0 1.93 12C3.23 16.34 7.24 19.5 12 19.5c.99 0 1.95-.14 2.86-.4" />
      <path d="M6.23 6.23A10.45 10.45 0 0 1 12 4.5c4.76 0 8.77 3.16 10.07 7.5a10.52 10.52 0 0 1-4.3 5.77" />
      <path d="M3 3l18 18" />
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
    </svg>
  );
}
