import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import JobsPage from "./pages/JobsPage";
import SetupPage from "./pages/SetupPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen w-full bg-[#f7f8f4] text-[#18342f]">
        <Navbar />
        <main className="mx-auto w-full max-w-6xl px-5 pb-20 pt-10 sm:px-8 sm:pt-14">
          <Routes>
            <Route path="/" element={<SetupPage />} />
            <Route path="/jobs" element={<JobsPage />} />
          </Routes>
        </main>
        <footer className="border-t border-[#dce5dc] px-5 py-6 text-center text-xs text-[#668078]">
          hiremenow · A more thoughtful way to find your next role.
        </footer>
      </div>
    </BrowserRouter>
  );
}
