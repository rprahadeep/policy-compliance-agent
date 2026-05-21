import React from "react";
import { Database, Loader2, UploadCloud } from "./Icon.js";

export function AppHeader({ onIngest, ingesting }) {
  return (
    <header className="app-header">
      <div className="brand-mark">
        <Database size={22} />
      </div>
      <div className="brand-copy">
        <span>Policy intelligence console</span>
        <h1>Compliance Decision Desk</h1>
      </div>
      <button className="button button-dark" onClick={onIngest} disabled={ingesting}>
        {ingesting ? <Loader2 className="spin" size={17} /> : <UploadCloud size={17} />}
        Sync policy index
      </button>
    </header>
  );
}
