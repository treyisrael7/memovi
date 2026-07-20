import { Shell } from "./components/Shell";
import { AppStateProvider } from "./state/AppStateContext";
import "./styles/theme.css";
import "./styles/shell.css";

function App() {
  return (
    <AppStateProvider>
      <Shell />
    </AppStateProvider>
  );
}

export default App;
