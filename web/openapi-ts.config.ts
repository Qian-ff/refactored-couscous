import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "../others/contracts/openapi.json",
  output: "./src/client",

  plugins: [
    { name: "@hey-api/client-axios", throwOnError: true },
    { name: "@hey-api/typescript", case: "preserve", definitions: {
      case: "preserve",
      // FastAPI qualifies colliding C1 names. Keep the released material DTO names stable for D.
      name: (name: string): string => name.startsWith("app__domains__content__views__")
        ? name.slice("app__domains__content__views__".length) : name,
    } },
    {
      name: "@hey-api/sdk",
      operations: {
        // NOTE: this doesn't allow tree-shaking
        strategy: "byTags",
        methods: "static",
        containerName: "{{name}}Service",
        methodName: (name: string): string => name.replace(/^[^-]*-/, ""),
      },
    },
  ],
})
