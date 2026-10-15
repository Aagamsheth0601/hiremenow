import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import JobsPage from "./pages/JobsPage";
import SetupPage from "./pages/SetupPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell min-h-screen w-full bg-[#f3f5f9] text-[#172b4d]">
        <div className="ambient-background" aria-hidden="true"><span /><span /><span /></div>
        <Navbar />
        <main className="mx-auto w-full max-w-7xl px-5 pb-20 pt-10 sm:px-8 sm:pt-14">
          <Routes>
            <Route path="/" element={<SetupPage />} />
            <Route path="/jobs" element={<JobsPage />} />
          </Routes>
        </main>
        <footer className="border-t border-[#dce2ec] px-5 py-6 text-center text-xs text-[#64748b]">
          hiremenow · YC startup jobs, matched to your experience.
        </footer>
      </div>
    </BrowserRouter>
  );
}
