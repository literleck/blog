// highlight.js 11.11.1 (core, C and shell only), vendored from cdnjs (design spec §5.3).
import hljs from "./core.min.js";
import c from "./languages/c.min.js";
import bash from "./languages/bash.min.js";

hljs.registerLanguage("c", c);
hljs.registerLanguage("bash", bash);
hljs.highlightAll();
