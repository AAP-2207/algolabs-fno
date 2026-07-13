import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import OptionChainPage from "./pages/OptionChainPage";
import GreeksPage from "./pages/GreeksPage";
import PnlPage from "./pages/PnlPage";
import DosPage from "./pages/DosPage";
import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 relative">
          <Routes>
            <Route path="/chain" element={
              <ErrorBoundary>
                <OptionChainPage />
              </ErrorBoundary>
            } />
            <Route path="/greeks" element={<GreeksPage />} />
            <Route path="/pnl" element={<PnlPage />} />
            <Route path="/dos" element={<DosPage />} />
            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/chain" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
