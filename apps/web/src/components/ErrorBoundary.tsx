import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Application error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="auth-screen">
          <section className="auth-card">
            <p className="eyebrow">Global fallback</p>
            <h1>Something broke in the control plane.</h1>
            <p className="muted">
              The UI hit an unexpected state. Reload to retry with a fresh session and route state.
            </p>
            <button className="button primary" onClick={() => window.location.reload()}>
              Retry the session
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
