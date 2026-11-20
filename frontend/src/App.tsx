import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import JobsPage from "./pages/JobsPage";
import SetupPage from "./pages/SetupPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell min-h-screen w-full">
        <Navbar />
        <main className="mx-auto w-full max-w-7xl px-4 pb-16 pt-6 sm:px-8 sm:pt-9">
          <Routes>
            <Route path="/" element={<SetupPage />} />
            <Route path="/jobs" element={<JobsPage />} />
          </Routes>
        </main>
        <footer className="border-t border-[#d6dfd6] px-5 py-6 text-center text-xs text-[#64748b]">
          hiremenow · YC startup jobs, matched to your experience.
        </footer>
      </div>
    </BrowserRouter>
  );
}
