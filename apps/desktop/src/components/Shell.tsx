import { MainContent } from "./MainContent";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";
import { TopBar } from "./TopBar";

export function Shell() {
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <TopBar />
        <MainContent />
        <StatusBar />
      </div>
    </div>
  );
}
