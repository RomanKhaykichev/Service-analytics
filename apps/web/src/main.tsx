console.log("VITE env:", import.meta.env.VITE_API_URL, import.meta.env.VITE_DEV_USER_ID);

import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

(window as any).__APP_ENV = {
  API_URL: import.meta.env.VITE_API_URL,
  DEV_USER_ID: import.meta.env.VITE_DEV_USER_ID,
};

console.log("APP_ENV", (window as any).__APP_ENV);

createRoot(document.getElementById("root")!).render(<App />);
