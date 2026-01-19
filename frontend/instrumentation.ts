import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "guilde_lite_tdd_sprint-frontend",
  });
}
