const THEME_BOOTSTRAP = `
(function () {
  try {
    var raw = localStorage.getItem("rashid-theme");
    var preset = "royal-violet";
    var mode = "dark";
    if (raw) {
      var parsed = JSON.parse(raw);
      if (parsed && parsed.preset) preset = parsed.preset;
      if (parsed && parsed.mode) mode = parsed.mode;
    }
    var root = document.documentElement;
    root.setAttribute("data-preset", preset);
    var resolved = mode;
    if (mode === "system") {
      resolved = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    root.classList.toggle("dark", resolved === "dark");
    root.classList.toggle("light", resolved === "light");
  } catch (e) {
    document.documentElement.classList.add("dark");
    document.documentElement.setAttribute("data-preset", "royal-violet");
  }
})();
`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />;
}
