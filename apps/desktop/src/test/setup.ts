import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom does not implement layout APIs used by ChatPage auto-scroll.
Element.prototype.scrollIntoView = function scrollIntoView() {
  return undefined;
};

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
