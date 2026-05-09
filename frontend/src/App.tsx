import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import JobsPage from "./pages/JobsPage";
import SetupPage from "./pages/SetupPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen w-full bg-zinc-50">
        <Navbar />
        <main className="mx-auto w-full max-w-3xl px-6 py-10">
          <Routes>
            <Route path="/" element={<SetupPage />} />
            <Route path="/jobs" element={<JobsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
