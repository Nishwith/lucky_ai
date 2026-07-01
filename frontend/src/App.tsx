import { LuckyProvider } from "./context/LuckyContext";
import { TopBar } from "./components/TopBar";
import { Sidebar } from "./components/Sidebar";
import { ChatPanel } from "./components/ChatPanel";
import { InputDock } from "./components/InputDock";
import { PermissionModal } from "./components/PermissionModal";
import "./App.css";

function AppContent() {
  return (
    <div className="hud-root">
      {/* Ambient background layers */}
      <div className="hud-grid" />
      <div className="hud-vignette" />
      <div className="scan-line" />

      {/* Top status bar */}
      <TopBar />

      <div className="hud-body">
        {/* Sidebar with embedded telemetry */}
        <Sidebar />

        {/* Main chat area */}
        <main className="hud-main">
          <ChatPanel />
          <InputDock />
        </main>
      </div>

      {/* OS Permission Modal */}
      <PermissionModal />
    </div>
  );
}

export default function App() {
  return (
    <LuckyProvider>
      <AppContent />
    </LuckyProvider>
  );
}
