import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

const eslintConfig = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  ...coreWebVitals,
  ...typescript,
  {
    // Pinned explicitly: eslint-plugin-react's automatic version detection
    // uses an ESLint 9 context API that was removed in ESLint 10.
    settings: { react: { version: "19.2" } },
  },
];

export default eslintConfig;
