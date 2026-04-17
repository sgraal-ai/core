"use client";
import { useState } from "react";

interface ErrorBannerProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorBanner({ message = "Unable to load data — check your connection", onRetry }: ErrorBannerProps) {
  return (
    <div style={{
      background: "#fef2f2",
      border: "1px solid #dc2626",
      borderRadius: "8px",
      padding: "16px",
      marginBottom: "16px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
    }}>
      <span style={{ color: "#991b1b", fontSize: "14px" }}>{message}</span>
      {onRetry && (
        <button onClick={onRetry} style={{
          padding: "6px 12px",
          background: "#dc2626",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          fontSize: "13px",
          cursor: "pointer",
        }}>
          Retry
        </button>
      )}
    </div>
  );
}
