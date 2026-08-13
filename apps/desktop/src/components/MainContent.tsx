import { useEffect, useState } from "react";

import { ActivityPage } from "./ActivityPage";
import { ChatPage } from "./ChatPage";
import { CollectionsPage } from "./CollectionsPage";
import { ConnectorsPage } from "./ConnectorsPage";
import { DocumentsPage } from "./DocumentsPage";
import { HomePage } from "./HomePage";
import { KnowledgeExplorerPage } from "./KnowledgeExplorerPage";
import { SearchPage } from "./SearchPage";
import { SettingsPage } from "./SettingsPage";
import { TagsPage } from "./TagsPage";
import { WorkflowsPage } from "./WorkflowsPage";
import { getPage } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";

export function MainContent() {
  const { activePage, chatSeed } = useAppState();
  const page = getPage(activePage);
  const [chatMounted, setChatMounted] = useState(false);

  useEffect(() => {
    if (page.id === "chat" || chatSeed) {
      setChatMounted(true);
    }
  }, [page.id, chatSeed]);

  let body = null;
  switch (page.id) {
    case "chat":
      break;
    case "knowledge":
      body = <KnowledgeExplorerPage />;
      break;
    case "collections":
      body = <CollectionsPage />;
      break;
    case "tags":
      body = <TagsPage />;
      break;
    case "workflows":
      body = <WorkflowsPage />;
      break;
    case "documents":
      body = <DocumentsPage />;
      break;
    case "connectors":
      body = <ConnectorsPage />;
      break;
    case "search":
      body = <SearchPage />;
      break;
    case "activity":
      body = <ActivityPage />;
      break;
    case "settings":
      body = <SettingsPage />;
      break;
    case "home":
    default:
      body = <HomePage />;
      break;
  }

  return (
    <main className="content">
      {chatMounted ? (
        <div hidden={page.id !== "chat"}>
          <ChatPage />
        </div>
      ) : null}
      {page.id !== "chat" ? body : null}
    </main>
  );
}
