import { Shell } from "./components/Shell";
import { AuthGate } from "./components/AuthGate";
import { SessionExpiredDialog } from "./components/SessionExpiredDialog";
import { ToastProvider } from "./components/ui/ToastContext";
import { AppStateProvider, useAppState } from "./state/AppStateContext";
import "./styles/theme.css";
import "./styles/shell.css";
import "./styles/components.css";

function AppRoot() {
  const { authStatus } = useAppState();

  if (authStatus === "checking" || authStatus === "anonymous") {
    return <AuthGate />;
  }

  return (
    <>
      <Shell />
      <SessionExpiredDialog />
    </>
  );
}

function App() {
  return (
    <AppStateProvider>
      <ToastProvider>
        <AppRoot />
      </ToastProvider>
    </AppStateProvider>
  );
}

export default App;
