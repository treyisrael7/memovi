import { MainContent } from "./MainContent";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";

export function Shell() {
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <MainContent />
        <StatusBar />
      </div>
    </div>
  );
}
