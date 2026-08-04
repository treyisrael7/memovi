import { Shell } from "./components/Shell";
import { ToastProvider } from "./components/ui/ToastContext";
import { AppStateProvider } from "./state/AppStateContext";
import "./styles/theme.css";
import "./styles/shell.css";

function App() {
  return (
    <AppStateProvider>
      <ToastProvider>
        <Shell />
      </ToastProvider>
    </AppStateProvider>
  );
}

export default App;
